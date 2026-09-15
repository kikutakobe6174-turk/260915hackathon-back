from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.llm.client import LlmCallError, call_structured, image_part, text_part
from app.llm.errors import LlmFeatureError
from app.llm.prompt_loader import load_prompt
from app.llm.schemas import TrendDraftLlmOutput
from app.models import Format, LlmJob, Test, Unit
from app.services.llm_job_service import save_llm_job


def generate_trend_draft(
    db: Session,
    settings: Settings,
    test: Test,
    image_base64: str,
    media_type: str,
    user_id: int,
) -> tuple[LlmJob, list[dict]]:
    units = db.query(Unit).filter(Unit.textbook_id == test.textbook_id).order_by(Unit.order_no).all()
    formats = db.query(Format).order_by(Format.id).all()
    valid_unit_ids = {u.id for u in units}
    valid_format_ids = {f.id for f in formats}

    prompt = load_prompt("trend_draft.txt").format(
        units="\n".join(f"- id={u.id}: {u.name}" for u in units) or "(なし)",
        formats="\n".join(f"- id={f.id}: {f.name}" for f in formats) or "(なし)",
    )

    request_params = {
        "test_id": test.id,
        "candidate_unit_ids": sorted(valid_unit_ids),
        "candidate_format_ids": sorted(valid_format_ids),
    }

    try:
        raw = call_structured(
            settings,
            input_parts=[image_part(image_base64, media_type), text_part(prompt)],
            json_schema=TrendDraftLlmOutput.model_json_schema(),
        )
        parsed = TrendDraftLlmOutput.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        save_llm_job(
            db,
            kind="trend",
            model=settings.gemini_model,
            request_params=request_params,
            response_json=None,
            status="failed",
            error_message=str(exc),
            created_by=user_id,
        )
        raise LlmFeatureError(str(exc)) from exc

    items = []
    for item in parsed.items:
        unit_id = item.unit_id if item.unit_id in valid_unit_ids else None
        format_id = item.format_id if item.format_id in valid_format_ids else None
        difficulty = min(max(item.difficulty, 1), 3)
        points = max(item.points, 0)
        confidence = min(max(item.confidence, 0.0), 1.0)
        items.append(
            {
                "question_no": item.question_no,
                "unit_id": unit_id,
                "format_id": format_id,
                "points": points,
                "difficulty": difficulty,
                "confidence": confidence,
            }
        )

    job = save_llm_job(
        db,
        kind="trend",
        model=settings.gemini_model,
        request_params=request_params,
        response_json={"items": items},
        status="done",
        error_message=None,
        created_by=user_id,
    )
    return job, items
