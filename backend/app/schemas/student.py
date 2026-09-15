from typing import Literal

from pydantic import BaseModel, ConfigDict

Level = Literal["A", "B", "C"]


class StudentCreate(BaseModel):
    student_code: str
    school_id: int
    grade: str
    level: Level
    active: bool = True


class StudentUpdate(BaseModel):
    student_code: str
    school_id: int
    grade: str
    level: Level
    active: bool


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_code: str
    school_id: int
    grade: str
    level: str
    active: bool


class StudentImportRow(BaseModel):
    student_code: str
    school_name: str
    grade: str
    level: Level


class StudentImportRequest(BaseModel):
    rows: list[StudentImportRow]
