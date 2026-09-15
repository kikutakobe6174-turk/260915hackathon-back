from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import (
    AnswerSheet,
    Attempt,
    Lesson,
    Problem,
    Student,
    Unit,
    User,
    WorksheetItem,
)
from app.schemas.answer_sheet import (
    AnswerSheetDetail,
    AnswerSheetItemDetail,
    AttemptOut,
    AttemptsPutRequest,
    AttemptsPutResponse,
    AttemptWarning,
    ConfirmRequest,
    ConfirmResponse,
)
from app.services.attempt_validation import build_warnings
from app.services.lookup import get_or_404

router = APIRouter(prefix="/answer-sheets", tags=["answer-sheets"])


def _build_detail(answer_sheet: AnswerSheet, db: Session) -> AnswerSheetDetail:
    student = get_or_404(db, Student, answer_sheet.student_id, "生徒")
    lesson = get_or_404(db, Lesson, answer_sheet.lesson_id, "授業回")

    worksheet_items = (
        db.query(WorksheetItem)
        .filter(WorksheetItem.worksheet_id == answer_sheet.worksheet_id)
        .order_by(WorksheetItem.sort_order)
        .all()
    )
    problems = {p.id: p for p in db.query(Problem).all()}
    units = {u.id: u.name for u in db.query(Unit.id, Unit.name).all()}
    attempts = {
        a.worksheet_item_id: a
        for a in db.query(Attempt).filter(Attempt.answer_sheet_id == answer_sheet.id).all()
    }

    items = []
    for wi in worksheet_items:
        problem = problems.get(wi.problem_id)
        attempt = attempts.get(wi.id)
        items.append(
            AnswerSheetItemDetail(
                worksheet_item_id=wi.id,
                item_no=wi.item_no,
                sort_order=wi.sort_order,
                problem_id=wi.problem_id,
                is_return=wi.is_return,
                parent_item_id=wi.parent_item_id,
                unit_id=problem.unit_id if problem else 0,
                unit_name=units.get(problem.unit_id, "") if problem else "",
                attempt=(
                    AttemptOut(
                        is_correct=attempt.is_correct,
                        hint_step=attempt.hint_step,
                        went_return=attempt.went_return,
                        red_card=attempt.red_card,
                        memo=attempt.memo,
                    )
                    if attempt
                    else None
                ),
            )
        )

    return AnswerSheetDetail(
        id=answer_sheet.id,
        student_id=answer_sheet.student_id,
        student_code=student.student_code,
        lesson_id=answer_sheet.lesson_id,
        worksheet_id=answer_sheet.worksheet_id,
        status=answer_sheet.status,
        source=answer_sheet.source,
        llm_job_id=answer_sheet.llm_job_id,
        confirmed_by=answer_sheet.confirmed_by,
        confirmed_at=answer_sheet.confirmed_at,
        round=lesson.round,
        items=items,
    )


@router.get("/{answer_sheet_id}", response_model=AnswerSheetDetail)
def get_answer_sheet(answer_sheet_id: int, db: Session = Depends(get_db)) -> AnswerSheetDetail:
    answer_sheet = get_or_404(db, AnswerSheet, answer_sheet_id, "解答用紙")
    return _build_detail(answer_sheet, db)


@router.put("/{answer_sheet_id}/attempts", response_model=AttemptsPutResponse)
def put_attempts(
    answer_sheet_id: int, payload: AttemptsPutRequest, db: Session = Depends(get_db)
) -> AttemptsPutResponse:
    answer_sheet = get_or_404(db, AnswerSheet, answer_sheet_id, "解答用紙")

    if answer_sheet.status == "confirmed":
        raise AppError(
            code="CONFLICT",
            message="確定済みの解答用紙は編集できません",
            status_code=409,
        )

    lesson = get_or_404(db, Lesson, answer_sheet.lesson_id, "授業回")

    valid_item_ids = {
        wi.id
        for wi in db.query(WorksheetItem.id).filter(WorksheetItem.worksheet_id == answer_sheet.worksheet_id).all()
    }
    for a in payload.attempts:
        if a.worksheet_item_id not in valid_item_ids:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"worksheet_item_id={a.worksheet_item_id} はこの冊子に含まれていません",
                status_code=400,
            )

    existing = {
        a.worksheet_item_id: a
        for a in db.query(Attempt).filter(Attempt.answer_sheet_id == answer_sheet_id).all()
    }

    for a in payload.attempts:
        row = existing.get(a.worksheet_item_id)
        if row is None:
            row = Attempt(
                answer_sheet_id=answer_sheet_id,
                worksheet_item_id=a.worksheet_item_id,
                round=lesson.round,
                is_correct=a.is_correct,
                hint_step=a.hint_step,
                went_return=a.went_return,
                red_card=a.red_card,
                memo=a.memo,
            )
            db.add(row)
        else:
            row.is_correct = a.is_correct
            row.hint_step = a.hint_step
            row.went_return = a.went_return
            row.red_card = a.red_card
            row.memo = a.memo

    if answer_sheet.status in ("empty", "in_progress", "llm_draft"):
        answer_sheet.status = "in_progress"

    db.commit()

    worksheet_items = (
        db.query(WorksheetItem).filter(WorksheetItem.worksheet_id == answer_sheet.worksheet_id).all()
    )
    all_attempts = {
        a.worksheet_item_id: a
        for a in db.query(Attempt).filter(Attempt.answer_sheet_id == answer_sheet_id).all()
    }
    submitted_ids = {a.worksheet_item_id for a in payload.attempts}
    warnings = build_warnings(worksheet_items, all_attempts, submitted_ids)

    return AttemptsPutResponse(
        saved=len(payload.attempts),
        warnings=[AttemptWarning(**w) for w in warnings],
    )


@router.post("/{answer_sheet_id}/confirm", response_model=ConfirmResponse)
def confirm_answer_sheet(
    answer_sheet_id: int, payload: ConfirmRequest, db: Session = Depends(get_db)
) -> ConfirmResponse:
    answer_sheet = get_or_404(db, AnswerSheet, answer_sheet_id, "解答用紙")
    get_or_404(db, User, payload.user_id, "ユーザー")

    answer_sheet.status = "confirmed"
    answer_sheet.confirmed_by = payload.user_id
    answer_sheet.confirmed_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(answer_sheet)

    next_sheet = (
        db.query(AnswerSheet)
        .filter(
            AnswerSheet.lesson_id == answer_sheet.lesson_id,
            AnswerSheet.status != "confirmed",
            AnswerSheet.id != answer_sheet.id,
        )
        .order_by(AnswerSheet.id)
        .first()
    )

    return ConfirmResponse(
        answer_sheet=_build_detail(answer_sheet, db),
        next_answer_sheet_id=next_sheet.id if next_sheet else None,
    )
