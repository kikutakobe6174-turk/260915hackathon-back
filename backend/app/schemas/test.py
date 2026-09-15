from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

TestKind = Literal["past", "target"]


class TestCreate(BaseModel):
    school_id: int
    textbook_id: int
    year: int
    grade: str
    term: str
    kind: TestKind
    unit_ids: list[int] = []


class TestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    textbook_id: int
    year: int
    grade: str
    term: str
    kind: str
    image_discarded_at: datetime | None
    unit_ids: list[int]
