from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import Test, TestScope, Unit, UnitPrerequisite, User
from app.schemas.prerequisite import (
    PrerequisiteOut,
    PrerequisitePutRequest,
    PrerequisiteReviewRequest,
    TestPrerequisitesOut,
    UnitPrerequisiteGroup,
)
from app.services.lookup import get_or_404

router = APIRouter(tags=["prerequisites"])


def _row_to_out(row: UnitPrerequisite, unit_names: dict[int, str]) -> PrerequisiteOut:
    return PrerequisiteOut(
        unit_id=row.unit_id,
        prerequisite_unit_id=row.prerequisite_unit_id,
        prerequisite_unit_name=unit_names.get(row.prerequisite_unit_id, ""),
        reason=row.reason,
        teacher_note=row.teacher_note,
        source=row.source,
        llm_job_id=row.llm_job_id,
        confirmed=row.confirmed,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
    )


@router.get("/tests/{test_id}/prerequisites", response_model=TestPrerequisitesOut)
def get_test_prerequisites(test_id: int, db: Session = Depends(get_db)) -> TestPrerequisitesOut:
    get_or_404(db, Test, test_id, "テスト")

    scope_unit_ids = [
        row.unit_id for row in db.query(TestScope.unit_id).filter(TestScope.test_id == test_id).all()
    ]
    units = db.query(Unit).filter(Unit.id.in_(scope_unit_ids)).order_by(Unit.order_no).all() if scope_unit_ids else []
    unit_names = {u.id: u.name for u in db.query(Unit.id, Unit.name).all()}

    groups: list[UnitPrerequisiteGroup] = []
    for unit in units:
        rows = (
            db.query(UnitPrerequisite)
            .filter(UnitPrerequisite.unit_id == unit.id)
            .order_by(UnitPrerequisite.prerequisite_unit_id)
            .all()
        )
        confirmed = len(rows) > 0 and all(r.confirmed for r in rows)
        groups.append(
            UnitPrerequisiteGroup(
                unit_id=unit.id,
                unit_name=unit.name,
                confirmed=confirmed,
                prerequisites=[_row_to_out(r, unit_names) for r in rows],
            )
        )

    return TestPrerequisitesOut(test_id=test_id, units=groups)


@router.put("/units/{unit_id}/prerequisites", response_model=list[PrerequisiteOut])
def put_unit_prerequisites(
    unit_id: int, payload: PrerequisitePutRequest, db: Session = Depends(get_db)
) -> list[PrerequisiteOut]:
    get_or_404(db, Unit, unit_id, "単元")
    get_or_404(db, User, payload.user_id, "ユーザー")

    for item in payload.items:
        if item.prerequisite_unit_id == unit_id:
            raise AppError(
                code="VALIDATION_ERROR", message="単元自身を前提単元にはできません", status_code=400
            )
        get_or_404(db, Unit, item.prerequisite_unit_id, "前提単元")

    existing = {
        r.prerequisite_unit_id: r
        for r in db.query(UnitPrerequisite).filter(UnitPrerequisite.unit_id == unit_id).all()
    }
    seen: set[int] = set()

    for item in payload.items:
        row = existing.get(item.prerequisite_unit_id)
        if row is None:
            row = UnitPrerequisite(
                unit_id=unit_id,
                prerequisite_unit_id=item.prerequisite_unit_id,
                reason=item.reason,
                source=item.source,
                llm_job_id=item.llm_job_id,
                confirmed=False,
            )
            db.add(row)
        else:
            row.reason = item.reason
            row.source = item.source
            row.llm_job_id = item.llm_job_id
        seen.add(item.prerequisite_unit_id)

    for prereq_unit_id, row in existing.items():
        if prereq_unit_id not in seen:
            db.delete(row)

    db.commit()

    unit_names = {u.id: u.name for u in db.query(Unit.id, Unit.name).all()}
    rows = (
        db.query(UnitPrerequisite)
        .filter(UnitPrerequisite.unit_id == unit_id)
        .order_by(UnitPrerequisite.prerequisite_unit_id)
        .all()
    )
    return [_row_to_out(r, unit_names) for r in rows]


@router.post(
    "/units/{unit_id}/prerequisites/{prerequisite_unit_id}/review",
    response_model=PrerequisiteOut,
)
def review_unit_prerequisite(
    unit_id: int,
    prerequisite_unit_id: int,
    payload: PrerequisiteReviewRequest,
    db: Session = Depends(get_db),
) -> PrerequisiteOut:
    get_or_404(db, User, payload.user_id, "ユーザー")

    row = (
        db.query(UnitPrerequisite)
        .filter(
            UnitPrerequisite.unit_id == unit_id,
            UnitPrerequisite.prerequisite_unit_id == prerequisite_unit_id,
        )
        .first()
    )
    if row is None:
        raise AppError(code="NOT_FOUND", message="前提単元が見つかりません", status_code=404)

    if payload.teacher_note is not None:
        row.teacher_note = payload.teacher_note

    row.confirmed = payload.confirmed
    if payload.confirmed:
        row.reviewed_by = payload.user_id
        row.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    else:
        row.reviewed_by = None
        row.reviewed_at = None

    db.commit()

    unit_names = {u.id: u.name for u in db.query(Unit.id, Unit.name).all()}
    db.refresh(row)
    return _row_to_out(row, unit_names)
