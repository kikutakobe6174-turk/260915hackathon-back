from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import Format, Hint, Problem, ProblemPrerequisite, Unit, User
from app.schemas.problem import ProblemIn, ProblemOut, ProblemReviewRequest
from app.services.lookup import get_or_404

router = APIRouter(prefix="/problems", tags=["problems"])


def _missing_return_units(db: Session, prerequisite_unit_ids: list[int]) -> list[int]:
    if not prerequisite_unit_ids:
        return []
    reviewed_return_unit_ids = {
        row.unit_id
        for row in db.query(Problem.unit_id)
        .filter(
            Problem.unit_id.in_(prerequisite_unit_ids),
            Problem.is_return.is_(True),
            Problem.status == "reviewed",
        )
        .distinct()
        .all()
    }
    return [uid for uid in prerequisite_unit_ids if uid not in reviewed_return_unit_ids]


def _to_out(problem: Problem, db: Session) -> ProblemOut:
    unit = db.get(Unit, problem.unit_id)
    fmt = db.get(Format, problem.format_id)
    hints = db.query(Hint).filter(Hint.problem_id == problem.id).order_by(Hint.step).all()
    prereq_unit_ids = [
        row.unit_id
        for row in db.query(ProblemPrerequisite.unit_id)
        .filter(ProblemPrerequisite.problem_id == problem.id)
        .all()
    ]
    return ProblemOut(
        id=problem.id,
        unit_id=problem.unit_id,
        unit_name=unit.name if unit else "",
        format_id=problem.format_id,
        format_name=fmt.name if fmt else "",
        difficulty=problem.difficulty,
        body=problem.body,
        answer=problem.answer,
        explanation=problem.explanation,
        is_return=problem.is_return,
        status=problem.status,
        source=problem.source,
        llm_job_id=problem.llm_job_id,
        reviewed_by=problem.reviewed_by,
        reviewed_at=problem.reviewed_at,
        hints=[{"step": h.step, "body": h.body} for h in hints],
        prerequisite_unit_ids=prereq_unit_ids,
        prerequisites_missing_return=_missing_return_units(db, prereq_unit_ids),
    )


def _validate_refs(db: Session, payload: ProblemIn) -> None:
    get_or_404(db, Unit, payload.unit_id, "単元")
    get_or_404(db, Format, payload.format_id, "形式")
    for uid in payload.prerequisite_unit_ids:
        get_or_404(db, Unit, uid, "前提単元")


@router.get("", response_model=list[ProblemOut])
def list_problems(
    unit_id: int | None = Query(default=None),
    format_id: int | None = Query(default=None),
    difficulty: int | None = Query(default=None),
    status: str | None = Query(default=None),
    is_return: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ProblemOut]:
    q = db.query(Problem)
    if unit_id is not None:
        q = q.filter(Problem.unit_id == unit_id)
    if format_id is not None:
        q = q.filter(Problem.format_id == format_id)
    if difficulty is not None:
        q = q.filter(Problem.difficulty == difficulty)
    if status is not None:
        q = q.filter(Problem.status == status)
    if is_return is not None:
        q = q.filter(Problem.is_return == is_return)
    problems = q.order_by(Problem.id).all()
    return [_to_out(p, db) for p in problems]


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)) -> ProblemOut:
    problem = get_or_404(db, Problem, problem_id, "問題")
    return _to_out(problem, db)


@router.post("", response_model=ProblemOut, status_code=201)
def create_problem(payload: ProblemIn, db: Session = Depends(get_db)) -> ProblemOut:
    _validate_refs(db, payload)

    problem = Problem(
        unit_id=payload.unit_id,
        format_id=payload.format_id,
        difficulty=payload.difficulty,
        body=payload.body,
        answer=payload.answer,
        explanation=payload.explanation,
        is_return=payload.is_return,
        status="draft",
        source=payload.source,
        llm_job_id=payload.llm_job_id,
    )
    db.add(problem)
    db.flush()

    for step, body in enumerate(payload.hints, start=1):
        db.add(Hint(problem_id=problem.id, step=step, body=body))
    for uid in payload.prerequisite_unit_ids:
        db.add(ProblemPrerequisite(problem_id=problem.id, unit_id=uid))

    db.commit()
    return _to_out(problem, db)


@router.put("/{problem_id}", response_model=ProblemOut)
def update_problem(problem_id: int, payload: ProblemIn, db: Session = Depends(get_db)) -> ProblemOut:
    problem = get_or_404(db, Problem, problem_id, "問題")
    _validate_refs(db, payload)

    problem.unit_id = payload.unit_id
    problem.format_id = payload.format_id
    problem.difficulty = payload.difficulty
    problem.body = payload.body
    problem.answer = payload.answer
    problem.explanation = payload.explanation
    problem.is_return = payload.is_return
    problem.source = payload.source
    problem.llm_job_id = payload.llm_job_id

    db.query(Hint).filter(Hint.problem_id == problem_id).delete()
    for step, body in enumerate(payload.hints, start=1):
        db.add(Hint(problem_id=problem_id, step=step, body=body))

    db.query(ProblemPrerequisite).filter(ProblemPrerequisite.problem_id == problem_id).delete()
    for uid in payload.prerequisite_unit_ids:
        db.add(ProblemPrerequisite(problem_id=problem_id, unit_id=uid))

    db.commit()
    db.refresh(problem)
    return _to_out(problem, db)


@router.post("/{problem_id}/review", response_model=ProblemOut)
def review_problem(problem_id: int, payload: ProblemReviewRequest, db: Session = Depends(get_db)) -> ProblemOut:
    problem = get_or_404(db, Problem, problem_id, "問題")
    get_or_404(db, User, payload.user_id, "ユーザー")

    problem.status = "reviewed"
    problem.reviewed_by = payload.user_id
    problem.reviewed_at = datetime.now(UTC).replace(tzinfo=None)

    db.commit()
    db.refresh(problem)
    return _to_out(problem, db)
