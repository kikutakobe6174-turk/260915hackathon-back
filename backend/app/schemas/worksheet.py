from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Level = Literal["A", "B", "C"]


class WorksheetItemIn(BaseModel):
    problem_id: int
    is_return: bool = False
    parent_index: int | None = None  # index within this request's items array


class WorksheetCreate(BaseModel):
    level: Level
    items: list[WorksheetItemIn] = []


class WorksheetItemOut(BaseModel):
    id: int
    item_no: str
    sort_order: int
    problem_id: int
    is_return: bool
    parent_item_id: int | None


class WorksheetOut(BaseModel):
    id: int
    test_id: int
    level: str
    version: int
    printed_at: datetime | None
    locked: bool
    items: list[WorksheetItemOut]
