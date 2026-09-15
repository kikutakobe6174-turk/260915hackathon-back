from datetime import date

from pydantic import BaseModel, ConfigDict


class LessonCreate(BaseModel):
    test_id: int
    lesson_date: date
    class_name: str
    round: int


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_id: int
    lesson_date: date
    class_name: str
    round: int
