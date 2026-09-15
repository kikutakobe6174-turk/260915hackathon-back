from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import Attempt, Problem, Test, Worksheet, WorksheetItem
from app.schemas.worksheet import WorksheetCreate, WorksheetItemOut, WorksheetOut
from app.services.lookup import get_or_404

router = APIRouter(tags=["worksheets"])


def _is_locked(db: Session, worksheet_id: int) -> bool:
    return (
        db.query(Attempt.id)
        .join(WorksheetItem, Attempt.worksheet_item_id == WorksheetItem.id)
        .filter(WorksheetItem.worksheet_id == worksheet_id)
        .first()
        is not None
    )


def _to_out(worksheet: Worksheet, db: Session) -> WorksheetOut:
    items = (
        db.query(WorksheetItem)
        .filter(WorksheetItem.worksheet_id == worksheet.id)
        .order_by(WorksheetItem.sort_order)
        .all()
    )
    return WorksheetOut(
        id=worksheet.id,
        test_id=worksheet.test_id,
        level=worksheet.level,
        version=worksheet.version,
        printed_at=worksheet.printed_at,
        locked=_is_locked(db, worksheet.id),
        items=[
            WorksheetItemOut(
                id=i.id,
                item_no=i.item_no,
                sort_order=i.sort_order,
                problem_id=i.problem_id,
                is_return=i.is_return,
                parent_item_id=i.parent_item_id,
            )
            for i in items
        ],
    )


def _validate_and_build_items(db: Session, worksheet_id: int, payload_items) -> list[WorksheetItem]:
    n = len(payload_items)
    for idx, item in enumerate(payload_items):
        problem = get_or_404(db, Problem, item.problem_id, "問題")
        if problem.status != "reviewed":
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"確認済みでない問題は冊子に追加できません (problem_id={item.problem_id})",
                status_code=400,
            )
        if item.parent_index is not None and not (0 <= item.parent_index < n):
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"parent_index が範囲外です (index={idx})",
                status_code=400,
            )

    rows: list[WorksheetItem] = []
    main_no = 0
    return_no = 0
    for item in payload_items:
        if item.is_return:
            return_no += 1
            item_no = f"R-{return_no}"
        else:
            main_no += 1
            item_no = str(main_no)
        rows.append(
            WorksheetItem(
                worksheet_id=worksheet_id,
                item_no=item_no,
                sort_order=len(rows),
                problem_id=item.problem_id,
                is_return=item.is_return,
                parent_item_id=None,
            )
        )
        db.add(rows[-1])

    db.flush()

    for idx, item in enumerate(payload_items):
        if item.parent_index is not None:
            rows[idx].parent_item_id = rows[item.parent_index].id

    return rows


@router.get("/tests/{test_id}/worksheets", response_model=list[WorksheetOut])
def list_worksheets(test_id: int, db: Session = Depends(get_db)) -> list[WorksheetOut]:
    get_or_404(db, Test, test_id, "テスト")
    worksheets = (
        db.query(Worksheet)
        .filter(Worksheet.test_id == test_id)
        .order_by(Worksheet.level, Worksheet.version)
        .all()
    )
    return [_to_out(w, db) for w in worksheets]


@router.post("/tests/{test_id}/worksheets", response_model=WorksheetOut, status_code=201)
def create_worksheet(test_id: int, payload: WorksheetCreate, db: Session = Depends(get_db)) -> WorksheetOut:
    get_or_404(db, Test, test_id, "テスト")

    latest_version = (
        db.query(Worksheet.version)
        .filter(Worksheet.test_id == test_id, Worksheet.level == payload.level)
        .order_by(Worksheet.version.desc())
        .first()
    )
    next_version = (latest_version[0] + 1) if latest_version else 1

    worksheet = Worksheet(test_id=test_id, level=payload.level, version=next_version)
    db.add(worksheet)
    db.flush()

    _validate_and_build_items(db, worksheet.id, payload.items)

    db.commit()
    db.refresh(worksheet)
    return _to_out(worksheet, db)


@router.get("/worksheets/{worksheet_id}", response_model=WorksheetOut)
def get_worksheet(worksheet_id: int, db: Session = Depends(get_db)) -> WorksheetOut:
    worksheet = get_or_404(db, Worksheet, worksheet_id, "冊子")
    return _to_out(worksheet, db)


@router.put("/worksheets/{worksheet_id}", response_model=WorksheetOut)
def update_worksheet(worksheet_id: int, payload: WorksheetCreate, db: Session = Depends(get_db)) -> WorksheetOut:
    worksheet = get_or_404(db, Worksheet, worksheet_id, "冊子")

    if _is_locked(db, worksheet_id):
        raise AppError(
            code="CONFLICT",
            message="この冊子は既に解答記録があるため編集できません。新しい版を作成してください",
            status_code=409,
        )

    if payload.level != worksheet.level:
        raise AppError(code="VALIDATION_ERROR", message="レベルは変更できません", status_code=400)

    db.query(WorksheetItem).filter(WorksheetItem.worksheet_id == worksheet_id).delete()
    db.flush()

    _validate_and_build_items(db, worksheet_id, payload.items)

    db.commit()
    db.refresh(worksheet)
    return _to_out(worksheet, db)
