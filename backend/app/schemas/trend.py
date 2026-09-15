from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TrendSource = Literal["manual", "llm"]


class TrendItemIn(BaseModel):
    id: int | None = None
    unit_id: int | None = None
    format_id: int
    question_no: str
    points: int = Field(ge=0)
    difficulty: int = Field(ge=1, le=3)
    source: TrendSource = "manual"
    llm_job_id: int | None = None


class TrendPutRequest(BaseModel):
    user_id: int
    items: list[TrendItemIn]


class TrendItemOut(BaseModel):
    id: int
    test_id: int
    unit_id: int | None
    unit_name: str | None
    format_id: int
    format_name: str
    question_no: str
    points: int
    difficulty: int
    source: str
    llm_job_id: int | None
    reviewed: bool
    reviewed_by: int | None
    reviewed_at: datetime | None


class UnitTrendSummary(BaseModel):
    unit_id: int
    unit_name: str
    question_count: int
    point_ratio: float


class TestTrendsOut(BaseModel):
    test_id: int
    items: list[TrendItemOut]
    summary: list[UnitTrendSummary]
