from datetime import datetime

from pydantic import BaseModel, Field


class AnswerSheetAssignmentIn(BaseModel):
    student_id: int
    worksheet_id: int


class AnswerSheetsCreateRequest(BaseModel):
    assignments: list[AnswerSheetAssignmentIn]


class AnswerSheetListItem(BaseModel):
    id: int
    student_id: int
    student_code: str
    school_name: str
    worksheet_id: int
    worksheet_level: str
    status: str
    red_card_count: int


class AttemptOut(BaseModel):
    is_correct: bool
    hint_step: int
    went_return: bool
    red_card: bool
    memo: str | None


class AnswerSheetItemDetail(BaseModel):
    worksheet_item_id: int
    item_no: str
    sort_order: int
    problem_id: int
    is_return: bool
    parent_item_id: int | None
    unit_id: int
    unit_name: str
    attempt: AttemptOut | None


class AnswerSheetDetail(BaseModel):
    id: int
    student_id: int
    student_code: str
    lesson_id: int
    worksheet_id: int
    status: str
    source: str
    llm_job_id: int | None
    confirmed_by: int | None
    confirmed_at: datetime | None
    round: int
    items: list[AnswerSheetItemDetail]


class AttemptIn(BaseModel):
    worksheet_item_id: int
    is_correct: bool
    hint_step: int = Field(ge=0, le=3)
    went_return: bool = False
    red_card: bool = False
    memo: str | None = None


class AttemptsPutRequest(BaseModel):
    attempts: list[AttemptIn]


class AttemptWarning(BaseModel):
    worksheet_item_id: int
    code: str
    message: str


class AttemptsPutResponse(BaseModel):
    saved: int
    warnings: list[AttemptWarning]


class ConfirmRequest(BaseModel):
    user_id: int


class ConfirmResponse(BaseModel):
    answer_sheet: AnswerSheetDetail
    next_answer_sheet_id: int | None
