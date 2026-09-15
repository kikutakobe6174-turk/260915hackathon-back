from datetime import datetime
from typing import Literal

from pydantic import BaseModel

PrereqSource = Literal["manual", "llm"]


class PrerequisiteItemIn(BaseModel):
    prerequisite_unit_id: int
    reason: str | None = None
    source: PrereqSource = "manual"
    llm_job_id: int | None = None


class PrerequisitePutRequest(BaseModel):
    user_id: int
    items: list[PrerequisiteItemIn]


class PrerequisiteReviewRequest(BaseModel):
    user_id: int
    confirmed: bool
    teacher_note: str | None = None


class PrerequisiteOut(BaseModel):
    unit_id: int
    prerequisite_unit_id: int
    prerequisite_unit_name: str
    reason: str | None
    teacher_note: str | None
    source: str
    llm_job_id: int | None
    confirmed: bool
    reviewed_by: int | None
    reviewed_at: datetime | None


class UnitPrerequisiteGroup(BaseModel):
    unit_id: int
    unit_name: str
    confirmed: bool
    prerequisites: list[PrerequisiteOut]


class TestPrerequisitesOut(BaseModel):
    test_id: int
    units: list[UnitPrerequisiteGroup]
