from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ProblemSource = Literal["manual", "llm"]
ProblemStatus = Literal["draft", "reviewed"]


class ProblemIn(BaseModel):
    unit_id: int
    format_id: int
    difficulty: int = Field(ge=1, le=3)
    body: str
    answer: str
    explanation: str | None = None
    is_return: bool = False
    hints: list[str]
    prerequisite_unit_ids: list[int] = []
    source: ProblemSource = "manual"
    llm_job_id: int | None = None

    @field_validator("hints")
    @classmethod
    def _hints_must_be_three(cls, v: list[str]) -> list[str]:
        if len(v) != 3:
            raise ValueError("hints must contain exactly 3 steps")
        return v


class HintOut(BaseModel):
    step: int
    body: str


class ProblemOut(BaseModel):
    id: int
    unit_id: int
    unit_name: str
    format_id: int
    format_name: str
    difficulty: int
    body: str
    answer: str
    explanation: str | None
    is_return: bool
    status: str
    source: str
    llm_job_id: int | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    hints: list[HintOut]
    prerequisite_unit_ids: list[int]
    prerequisites_missing_return: list[int]


class ProblemReviewRequest(BaseModel):
    user_id: int
