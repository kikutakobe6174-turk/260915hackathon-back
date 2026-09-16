from pydantic import BaseModel, Field


class TrendDraftRequest(BaseModel):
    test_id: int
    user_id: int
    image_base64: str
    media_type: str = "image/jpeg"


class TrendDraftItemOut(BaseModel):
    question_no: str
    unit_id: int | None
    format_id: int | None
    points: int
    difficulty: int
    confidence: float


class TrendDraftResponse(BaseModel):
    job_id: int
    image_discarded: bool
    items: list[TrendDraftItemOut]


class PrereqSuggestRequest(BaseModel):
    unit_id: int
    user_id: int


class PrereqSuggestionOut(BaseModel):
    prerequisite_unit_id: int
    reason: str


class PrereqSuggestResponse(BaseModel):
    job_id: int
    suggestions: list[PrereqSuggestionOut]


class ProblemDraftRequest(BaseModel):
    unit_id: int
    format_id: int
    difficulty: int = Field(ge=1, le=3)
    prerequisite_unit_ids: list[int] = []
    is_return: bool = False
    count: int = Field(default=1, ge=1, le=5)
    user_id: int


class ProblemDraftHintOut(BaseModel):
    step: int
    body: str


class ProblemDraftItemOut(BaseModel):
    body: str
    answer: str
    explanation: str
    hints: list[ProblemDraftHintOut]
    prerequisite_unit_ids: list[int]


class ProblemDraftResponse(BaseModel):
    job_id: int
    drafts: list[ProblemDraftItemOut]


class TrendProblemDraftTarget(BaseModel):
    test_id: int
    unit_id: int


class TrendProblemDraftRequest(BaseModel):
    user_id: int
    targets: list[TrendProblemDraftTarget] = Field(min_length=1)


class TrendProblemDraftItemOut(BaseModel):
    test_id: int
    unit_id: int
    format_id: int
    difficulty: int
    body: str
    answer: str
    explanation: str
    hints: list[ProblemDraftHintOut]
    prerequisite_unit_ids: list[int]


class TrendProblemDraftResponse(BaseModel):
    job_id: int
    drafts: list[TrendProblemDraftItemOut]


class SheetDraftRequest(BaseModel):
    answer_sheet_id: int
    user_id: int
    image_base64: str
    media_type: str = "image/jpeg"


class SheetDraftRowOut(BaseModel):
    item_no: str
    worksheet_item_id: int | None
    is_correct: bool
    hint_step: int
    went_return: bool
    red_card: bool
    confidence: float


class SheetDraftResponse(BaseModel):
    job_id: int
    image_discarded: bool
    rows: list[SheetDraftRowOut]
