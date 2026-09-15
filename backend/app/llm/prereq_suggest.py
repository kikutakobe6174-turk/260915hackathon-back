from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.llm.client import LlmCallError, call_structured
from app.llm.errors import LlmFeatureError
from app.llm.prompt_loader import load_prompt
from app.llm.schemas import PrereqSuggestLlmOutput
from app.models import LlmJob, Unit
from app.services.llm_job_service import save_llm_job


def generate_prereq_suggestions(
    db: Session,
    settings: Settings,
    unit: Unit,
    user_id: int,
) -> tuple[LlmJob, list[dict]]:
    candidates = (
        db.query(Unit)
        .filter(Unit.textbook_id == unit.textbook_id, Unit.order_no < unit.order_no)
        .order_by(Unit.order_no)
        .all()
    )
    valid_ids = {u.id for u in candidates}

    prompt = load_prompt("prereq_suggest.txt").format(
        target_unit_name=unit.name,
        candidate_units="\n".join(f"- id={u.id}: {u.name}" for u in candidates) or "(候補なし)",
    )

    request_params = {"unit_id": unit.id, "candidate_unit_ids": sorted(valid_ids)}

    try:
        raw = call_structured(
            settings,
            input_parts=prompt,
            json_schema=PrereqSuggestLlmOutput.model_json_schema(),
        )
        parsed = PrereqSuggestLlmOutput.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        save_llm_job(
            db,
            kind="prereq",
            model=settings.gemini_model,
            request_params=request_params,
            response_json=None,
            status="failed",
            error_message=str(exc),
            created_by=user_id,
        )
        raise LlmFeatureError(str(exc)) from exc

    suggestions = [
        {"prerequisite_unit_id": s.prerequisite_unit_id, "reason": s.reason}
        for s in parsed.suggestions
        if s.prerequisite_unit_id in valid_ids and s.prerequisite_unit_id != unit.id
    ]

    job = save_llm_job(
        db,
        kind="prereq",
        model=settings.gemini_model,
        request_params=request_params,
        response_json={"suggestions": suggestions},
        status="done",
        error_message=None,
        created_by=user_id,
    )
    return job, suggestions
