from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import School, Test, TestScope, Textbook, Unit
from app.schemas.test import TestCreate, TestOut
from app.services.lookup import get_or_404

router = APIRouter(prefix="/tests", tags=["tests"])


def _to_out(test: Test, db: Session) -> TestOut:
    unit_ids = [
        row.unit_id for row in db.query(TestScope.unit_id).filter(TestScope.test_id == test.id).all()
    ]
    return TestOut(
        id=test.id,
        school_id=test.school_id,
        textbook_id=test.textbook_id,
        year=test.year,
        grade=test.grade,
        term=test.term,
        kind=test.kind,
        image_discarded_at=test.image_discarded_at,
        unit_ids=unit_ids,
    )


@router.get("", response_model=list[TestOut])
def list_tests(
    school_id: int | None = Query(default=None),
    kind: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[TestOut]:
    q = db.query(Test)
    if school_id is not None:
        q = q.filter(Test.school_id == school_id)
    if kind is not None:
        q = q.filter(Test.kind == kind)
    tests = q.order_by(Test.id.desc()).all()
    return [_to_out(t, db) for t in tests]


@router.get("/{test_id}", response_model=TestOut)
def get_test(test_id: int, db: Session = Depends(get_db)) -> TestOut:
    test = get_or_404(db, Test, test_id, "テスト")
    return _to_out(test, db)


@router.post("", response_model=TestOut, status_code=201)
def create_test(payload: TestCreate, db: Session = Depends(get_db)) -> TestOut:
    get_or_404(db, School, payload.school_id, "学校")
    get_or_404(db, Textbook, payload.textbook_id, "教科書")

    if payload.unit_ids:
        valid_unit_ids = {
            row.id
            for row in db.query(Unit.id)
            .filter(Unit.textbook_id == payload.textbook_id, Unit.id.in_(payload.unit_ids))
            .all()
        }
        invalid = set(payload.unit_ids) - valid_unit_ids
        if invalid:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"指定された教科書に属さない単元IDが含まれています: {sorted(invalid)}",
                status_code=400,
            )

    test = Test(
        school_id=payload.school_id,
        textbook_id=payload.textbook_id,
        year=payload.year,
        grade=payload.grade,
        term=payload.term,
        kind=payload.kind,
    )
    db.add(test)
    db.flush()

    for unit_id in payload.unit_ids:
        db.add(TestScope(test_id=test.id, unit_id=unit_id))

    db.commit()
    db.refresh(test)
    return _to_out(test, db)
