from collections import defaultdict

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AnswerSheet, Attempt, Lesson, Problem, Student, WorksheetItem
from app.schemas.stats import ProblemStatsItem, ProblemStatsOut


def compute_problem_stats(
    db: Session,
    settings: Settings,
    test_id: int | None = None,
    round_: int | None = None,
    level: str | None = None,
) -> ProblemStatsOut:
    q = (
        db.query(Attempt, WorksheetItem.problem_id)
        .join(WorksheetItem, Attempt.worksheet_item_id == WorksheetItem.id)
        .join(AnswerSheet, Attempt.answer_sheet_id == AnswerSheet.id)
        .join(Lesson, AnswerSheet.lesson_id == Lesson.id)
        .filter(AnswerSheet.status == "confirmed")
    )
    if test_id is not None:
        q = q.filter(Lesson.test_id == test_id)
    if round_ is not None:
        q = q.filter(Attempt.round == round_)
    if level is not None:
        q = q.join(Student, AnswerSheet.student_id == Student.id).filter(Student.level == level)

    rows = q.all()

    by_problem: dict[int, list[Attempt]] = defaultdict(list)
    for attempt, problem_id in rows:
        by_problem[problem_id].append(attempt)

    if not by_problem:
        return ProblemStatsOut(items=[])

    difficulties = {
        p.id: p.difficulty for p in db.query(Problem).filter(Problem.id.in_(by_problem.keys())).all()
    }

    items: list[ProblemStatsItem] = []
    for problem_id, attempts in by_problem.items():
        total = len(attempts)
        correct_no_hint = sum(1 for a in attempts if a.is_correct and a.hint_step == 0) / total

        correct_by_hint: dict[str, float] = {}
        for step in (1, 2, 3):
            correct_by_hint[str(step)] = sum(
                1 for a in attempts if a.is_correct and a.hint_step == step
            ) / total

        wrong_after_hint3 = sum(1 for a in attempts if not a.is_correct and a.hint_step == 3) / total

        by_round: dict[int, list[Attempt]] = defaultdict(list)
        for a in attempts:
            by_round[a.round].append(a)
        correct_by_round = {
            str(r): sum(1 for a in round_attempts if a.is_correct) / len(round_attempts)
            for r, round_attempts in sorted(by_round.items())
        }

        flags: list[str] = []
        difficulty = difficulties.get(problem_id)
        if difficulty == 1 and correct_no_hint < settings.low_accuracy_no_hint_threshold:
            flags.append("LOW_ACCURACY_NO_HINT")
        if wrong_after_hint3 >= settings.high_wrong_after_hint3_threshold:
            flags.append("WRONG_AFTER_HINT3_HIGH")

        items.append(
            ProblemStatsItem(
                problem_id=problem_id,
                attempts=total,
                correct_no_hint=correct_no_hint,
                correct_by_hint=correct_by_hint,
                wrong_after_hint3=wrong_after_hint3,
                correct_by_round=correct_by_round,
                flags=flags,
            )
        )

    items.sort(key=lambda i: i.problem_id)
    return ProblemStatsOut(items=items)
