from pydantic import BaseModel


class CoverageCell(BaseModel):
    unit_id: int
    format_id: int
    difficulty: int
    required: int
    reviewed: int
    draft: int


class CoverageOut(BaseModel):
    multiplier: int
    cells: list[CoverageCell]
    return_missing_unit_ids: list[int]
