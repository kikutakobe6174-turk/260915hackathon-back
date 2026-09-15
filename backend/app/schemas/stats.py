from pydantic import BaseModel


class ProblemStatsItem(BaseModel):
    problem_id: int
    attempts: int
    correct_no_hint: float
    correct_by_hint: dict[str, float]
    wrong_after_hint3: float
    correct_by_round: dict[str, float]
    flags: list[str]


class ProblemStatsOut(BaseModel):
    items: list[ProblemStatsItem]
