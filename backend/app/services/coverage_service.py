import math

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Format, Problem, Test, TestScope, TestTrend, UnitPrerequisite
from app.schemas.coverage import CoverageCell, CoverageOut


def _required_counts(db: Session, test: Test) -> dict[tuple[int, int, int], float]:
    past_test_ids = [
        row.id
        for row in db.query(Test.id)
        .filter(
            Test.school_id == test.school_id,
            Test.textbook_id == test.textbook_id,
            Test.kind == "past",
        )
        .all()
    ]
    if not past_test_ids:
        return {}

    rows = (
        db.query(
            TestTrend.unit_id,
            TestTrend.format_id,
            TestTrend.difficulty,
            func.count().label("cnt"),
        )
        .filter(
            TestTrend.test_id.in_(past_test_ids),
            TestTrend.reviewed.is_(True),
            TestTrend.unit_id.isnot(None),
        )
        .group_by(TestTrend.unit_id, TestTrend.format_id, TestTrend.difficulty)
        .all()
    )

    n = len(past_test_ids)
    return {(r.unit_id, r.format_id, r.difficulty): r.cnt / n for r in rows}


def compute_coverage(db: Session, test: Test, multiplier: int) -> CoverageOut:
    scope_unit_ids = [
        row.unit_id for row in db.query(TestScope.unit_id).filter(TestScope.test_id == test.id).all()
    ]
    format_ids = [row.id for row in db.query(Format.id).all()]

    required_avg = _required_counts(db, test)

    problem_counts: dict[tuple[int, int, int, str], int] = {}
    if scope_unit_ids:
        rows = (
            db.query(Problem.unit_id, Problem.format_id, Problem.difficulty, Problem.status, func.count())
            .filter(Problem.unit_id.in_(scope_unit_ids))
            .group_by(Problem.unit_id, Problem.format_id, Problem.difficulty, Problem.status)
            .all()
        )
        for unit_id, format_id, difficulty, status, cnt in rows:
            problem_counts[(unit_id, format_id, difficulty, status)] = cnt

    cells: list[CoverageCell] = []
    for unit_id in scope_unit_ids:
        for format_id in format_ids:
            for difficulty in (1, 2, 3):
                avg = required_avg.get((unit_id, format_id, difficulty), 0.0)
                required = math.ceil(avg * multiplier)
                reviewed = problem_counts.get((unit_id, format_id, difficulty, "reviewed"), 0)
                draft = problem_counts.get((unit_id, format_id, difficulty, "draft"), 0)
                if required == 0 and reviewed == 0 and draft == 0:
                    continue
                cells.append(
                    CoverageCell(
                        unit_id=unit_id,
                        format_id=format_id,
                        difficulty=difficulty,
                        required=required,
                        reviewed=reviewed,
                        draft=draft,
                    )
                )

    return_missing_unit_ids: list[int] = []
    if scope_unit_ids:
        prereq_unit_ids = {
            row.prerequisite_unit_id
            for row in db.query(UnitPrerequisite.prerequisite_unit_id)
            .filter(UnitPrerequisite.unit_id.in_(scope_unit_ids))
            .distinct()
            .all()
        }
        if prereq_unit_ids:
            has_return = {
                row.unit_id
                for row in db.query(Problem.unit_id)
                .filter(
                    Problem.unit_id.in_(prereq_unit_ids),
                    Problem.is_return.is_(True),
                    Problem.status == "reviewed",
                )
                .distinct()
                .all()
            }
            return_missing_unit_ids = sorted(prereq_unit_ids - has_return)

    return CoverageOut(multiplier=multiplier, cells=cells, return_missing_unit_ids=return_missing_unit_ids)
