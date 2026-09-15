from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.deps import get_db
from app.llm.errors import LlmFeatureError
from app.llm.prereq_suggest import generate_prereq_suggestions
from app.llm.problem_draft import generate_problem_drafts
from app.llm.sheet_draft import generate_sheet_draft
from app.llm.trend_draft import generate_trend_draft
from app.models import AnswerSheet, Format, Test, Unit, User
from app.schemas.llm import (
    PrereqSuggestRequest,
    PrereqSuggestResponse,
    ProblemDraftRequest,
    ProblemDraftResponse,
    SheetDraftRequest,
    SheetDraftResponse,
    TrendDraftRequest,
    TrendDraftResponse,
)
from app.services.lookup import get_or_404

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/trend-draft", response_model=TrendDraftResponse)
def llm_trend_draft(
    payload: TrendDraftRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TrendDraftResponse:
    test = get_or_404(db, Test, payload.test_id, "テスト")
    get_or_404(db, User, payload.user_id, "ユーザー")

    try:
        job, items = generate_trend_draft(db, settings, test, payload.image_base64, payload.media_type, payload.user_id)
    except LlmFeatureError as exc:
        raise AppError(code="LLM_ERROR", message=exc.message, status_code=502) from exc

    return TrendDraftResponse(job_id=job.id, image_discarded=True, items=items)


@router.post("/prereq-suggest", response_model=PrereqSuggestResponse)
def llm_prereq_suggest(
    payload: PrereqSuggestRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PrereqSuggestResponse:
    unit = get_or_404(db, Unit, payload.unit_id, "単元")
    get_or_404(db, User, payload.user_id, "ユーザー")

    try:
        job, suggestions = generate_prereq_suggestions(db, settings, unit, payload.user_id)
    except LlmFeatureError as exc:
        raise AppError(code="LLM_ERROR", message=exc.message, status_code=502) from exc

    return PrereqSuggestResponse(job_id=job.id, suggestions=suggestions)


@router.post("/problem-draft", response_model=ProblemDraftResponse)
def llm_problem_draft(
    payload: ProblemDraftRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ProblemDraftResponse:
    unit = get_or_404(db, Unit, payload.unit_id, "単元")
    format_ = get_or_404(db, Format, payload.format_id, "形式")
    get_or_404(db, User, payload.user_id, "ユーザー")
    prerequisite_units = [
        get_or_404(db, Unit, uid, "前提単元") for uid in payload.prerequisite_unit_ids
    ]

    try:
        job, drafts = generate_problem_drafts(
            db,
            settings,
            unit,
            format_,
            payload.difficulty,
            prerequisite_units,
            payload.is_return,
            payload.count,
            payload.user_id,
        )
    except LlmFeatureError as exc:
        raise AppError(code="LLM_ERROR", message=exc.message, status_code=502) from exc

    return ProblemDraftResponse(job_id=job.id, drafts=drafts)


@router.post("/sheet-draft", response_model=SheetDraftResponse)
def llm_sheet_draft(
    payload: SheetDraftRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SheetDraftResponse:
    answer_sheet = get_or_404(db, AnswerSheet, payload.answer_sheet_id, "解答用紙")
    get_or_404(db, User, payload.user_id, "ユーザー")

    try:
        job, rows = generate_sheet_draft(db, settings, answer_sheet, payload.image_base64, payload.media_type, payload.user_id)
    except LlmFeatureError as exc:
        raise AppError(code="LLM_ERROR", message=exc.message, status_code=502) from exc

    return SheetDraftResponse(job_id=job.id, image_discarded=True, rows=rows)
