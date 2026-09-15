"""Pydantic models describing the JSON we ask Gemini to return.

These are intentionally looser than our public API schemas (e.g. no strict
range constraints on a single field) so that one malformed field in a list
does not blow up parsing of the entire response; range/reference validation
against real DB rows happens in each app/llm/<feature>.py module afterwards.
"""

from pydantic import BaseModel


class TrendDraftLlmItem(BaseModel):
    question_no: str
    unit_id: int | None = None
    format_id: int | None = None
    points: int
    difficulty: int
    confidence: float = 0.5


class TrendDraftLlmOutput(BaseModel):
    items: list[TrendDraftLlmItem]


class PrereqSuggestionLlmItem(BaseModel):
    prerequisite_unit_id: int
    reason: str


class PrereqSuggestLlmOutput(BaseModel):
    suggestions: list[PrereqSuggestionLlmItem]


class ProblemDraftHintLlm(BaseModel):
    step: int
    body: str


class ProblemDraftLlmItem(BaseModel):
    body: str
    answer: str
    explanation: str
    hints: list[ProblemDraftHintLlm]


class ProblemDraftLlmOutput(BaseModel):
    drafts: list[ProblemDraftLlmItem]


class TrendProblemDraftLlmItem(BaseModel):
    test_id: int
    unit_id: int
    format_id: int
    difficulty: int
    body: str
    answer: str
    explanation: str
    hints: list[ProblemDraftHintLlm]
    prerequisite_unit_ids: list[int] = []


class TrendProblemDraftLlmOutput(BaseModel):
    drafts: list[TrendProblemDraftLlmItem]


class SheetDraftLlmRow(BaseModel):
    item_no: str
    is_correct: bool
    hint_step: int
    went_return: bool = False
    red_card: bool = False
    confidence: float = 0.5


class SheetDraftLlmOutput(BaseModel):
    rows: list[SheetDraftLlmRow]
