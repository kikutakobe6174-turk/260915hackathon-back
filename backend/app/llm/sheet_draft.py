from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.llm.client import LlmCallError, call_structured, image_part, text_part
from app.llm.errors import LlmFeatureError
from app.llm.prompt_loader import load_prompt
from app.llm.schemas import SheetDraftLlmOutput
from app.models import AnswerSheet, LlmJob, WorksheetItem
from app.services.llm_job_service import save_llm_job


def generate_sheet_draft(
    db: Session,
    settings: Settings,
    answer_sheet: AnswerSheet,
    image_base64: str,
    media_type: str,
    user_id: int,
) -> tuple[LlmJob, list[dict]]:
    items = (
        db.query(WorksheetItem)
        .filter(WorksheetItem.worksheet_id == answer_sheet.worksheet_id)
        .order_by(WorksheetItem.sort_order)
        .all()
    )
    item_no_to_id = {i.item_no: i.id for i in items}

    prompt = load_prompt("sheet_draft.txt").format(
        item_nos=", ".join(item_no_to_id.keys()) or "(なし)",
    )

    request_params = {
        "answer_sheet_id": answer_sheet.id,
        "candidate_item_nos": list(item_no_to_id.keys()),
    }

    try:
        raw = call_structured(
            settings,
            input_parts=[image_part(image_base64, media_type), text_part(prompt)],
            json_schema=SheetDraftLlmOutput.model_json_schema(),
        )
        parsed = SheetDraftLlmOutput.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        save_llm_job(
            db,
            kind="sheet",
            model=settings.gemini_model,
            request_params=request_params,
            response_json=None,
            status="failed",
            error_message=str(exc),
            created_by=user_id,
        )
        raise LlmFeatureError(str(exc)) from exc

    rows = []
    for r in parsed.rows:
        worksheet_item_id = item_no_to_id.get(r.item_no)
        hint_step = min(max(r.hint_step, 0), 3)
        confidence = min(max(r.confidence, 0.0), 1.0)
        rows.append(
            {
                "item_no": r.item_no,
                "worksheet_item_id": worksheet_item_id,
                "is_correct": r.is_correct,
                "hint_step": hint_step,
                "went_return": r.went_return,
                "red_card": r.red_card,
                "confidence": confidence,
            }
        )

    job = save_llm_job(
        db,
        kind="sheet",
        model=settings.gemini_model,
        request_params=request_params,
        response_json={"rows": rows},
        status="done",
        error_message=None,
        created_by=user_id,
    )

    answer_sheet.status = "llm_draft"
    answer_sheet.source = "llm"
    answer_sheet.llm_job_id = job.id
    db.commit()

    return job, rows
