from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.llm.client import LlmCallError, call_structured
from app.llm.errors import LlmFeatureError
from app.llm.prompt_loader import load_prompt
from app.llm.schemas import ProblemDraftLlmOutput
from app.models import Format, LlmJob, Unit
from app.services.llm_job_service import save_llm_job


def generate_problem_drafts(
    db: Session,
    settings: Settings,
    unit: Unit,
    format_: Format,
    difficulty: int,
    prerequisite_units: list[Unit],
    is_return: bool,
    count: int,
    user_id: int,
) -> tuple[LlmJob, list[dict]]:
    prompt = load_prompt("problem_draft.txt").format(
        count=count,
        unit_name=unit.name,
        format_name=format_.name,
        difficulty=difficulty,
        purpose="この単元でつまずいた生徒向けの、前提単元に立ち返る戻り問題" if is_return else "通常の演習問題",
        prerequisite_unit_names=", ".join(u.name for u in prerequisite_units) or "(特になし)",
    )

    request_params = {
        "unit_id": unit.id,
        "format_id": format_.id,
        "difficulty": difficulty,
        "prerequisite_unit_ids": [u.id for u in prerequisite_units],
        "is_return": is_return,
        "count": count,
    }

    try:
        raw = call_structured(
            settings,
            input_parts=prompt,
            json_schema=ProblemDraftLlmOutput.model_json_schema(),
        )
        parsed = ProblemDraftLlmOutput.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        save_llm_job(
            db,
            kind="problem",
            model=settings.gemini_model,
            request_params=request_params,
            response_json=None,
            status="failed",
            error_message=str(exc),
            created_by=user_id,
        )
        raise LlmFeatureError(str(exc)) from exc

    prerequisite_unit_ids = [u.id for u in prerequisite_units]
    drafts = []
    for draft in parsed.drafts:
        steps = sorted(h.step for h in draft.hints)
        if steps != [1, 2, 3]:
            continue  # spec: hints must be exactly 3 steps, discard otherwise
        ordered_hints = sorted(draft.hints, key=lambda h: h.step)
        drafts.append(
            {
                "body": draft.body,
                "answer": draft.answer,
                "explanation": draft.explanation,
                "hints": [{"step": h.step, "body": h.body} for h in ordered_hints],
                "prerequisite_unit_ids": prerequisite_unit_ids,
            }
        )

    job = save_llm_job(
        db,
        kind="problem",
        model=settings.gemini_model,
        request_params=request_params,
        response_json={"drafts": drafts},
        status="done",
        error_message=None,
        created_by=user_id,
    )
    return job, drafts
