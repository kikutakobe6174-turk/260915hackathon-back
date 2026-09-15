from collections import Counter

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.llm.client import LlmCallError, call_structured
from app.llm.errors import LlmFeatureError
from app.llm.prompt_loader import load_prompt
from app.llm.schemas import TrendProblemDraftLlmOutput
from app.models import Format, LlmJob, Test, TestTrend, Unit
from app.services.llm_job_service import save_llm_job


def generate_trend_problem_drafts(
    db: Session,
    settings: Settings,
    targets: list[tuple[Test, Unit]],
    user_id: int,
) -> tuple[LlmJob, list[dict]]:
    """Generate problem drafts from each (test, unit)'s reviewed出題傾向 (TestTrend rows).

    Targets without any reviewed trend data are skipped (nothing to base a
    problem on). If no target has trend data, no LLM call is made at all.
    """
    formats = db.query(Format).order_by(Format.id).all()
    format_names = {f.id: f.name for f in formats}
    valid_format_ids = set(format_names)
    format_candidates_text = "\n".join(f"- id={f.id}: {f.name}" for f in formats) or "(なし)"

    target_blocks: list[str] = []
    target_meta: dict[tuple[int, int], dict] = {}

    for test, unit in targets:
        key = (test.id, unit.id)
        if key in target_meta:
            continue

        trend_rows = (
            db.query(TestTrend)
            .filter(
                TestTrend.test_id == test.id,
                TestTrend.unit_id == unit.id,
                TestTrend.reviewed.is_(True),
            )
            .all()
        )
        if not trend_rows:
            continue  # no reviewed trend data for this test x unit -> nothing to base a draft on

        format_counts = Counter(r.format_id for r in trend_rows)
        format_summary = ", ".join(
            f"{format_names.get(fid, '?')}({cnt}問)" for fid, cnt in format_counts.most_common()
        )
        avg_difficulty = sum(r.difficulty for r in trend_rows) / len(trend_rows)
        fallback_format_id = format_counts.most_common(1)[0][0]

        prereq_candidates = (
            db.query(Unit)
            .filter(Unit.textbook_id == unit.textbook_id, Unit.order_no < unit.order_no)
            .order_by(Unit.order_no)
            .all()
        )
        prereq_candidate_ids = {u.id for u in prereq_candidates}
        prereq_lines = "\n".join(f"  - id={u.id}: {u.name}" for u in prereq_candidates) or "  (候補なし)"

        target_blocks.append(
            f"- test_id={test.id}, unit_id={unit.id}（単元名: {unit.name}）\n"
            f"  出題形式の傾向: {format_summary}\n"
            f"  難易度の傾向: 平均 {avg_difficulty:.1f}（1〜3の3段階）\n"
            f"  前提単元候補:\n{prereq_lines}"
        )
        target_meta[key] = {
            "fallback_format_id": fallback_format_id,
            "valid_prereq_ids": prereq_candidate_ids,
        }

    request_params = {
        "targets": [{"test_id": t.id, "unit_id": u.id} for t, u in targets],
        "resolved_targets": [{"test_id": tid, "unit_id": uid} for tid, uid in target_meta],
    }

    if not target_meta:
        job = save_llm_job(
            db,
            kind="trend_problem",
            model=settings.gemini_model,
            request_params=request_params,
            response_json={"drafts": []},
            status="done",
            error_message=None,
            created_by=user_id,
        )
        return job, []

    prompt = load_prompt("trend_problem_draft.txt").format(
        targets="\n".join(target_blocks),
        formats=format_candidates_text,
    )

    try:
        raw = call_structured(
            settings,
            input_parts=prompt,
            json_schema=TrendProblemDraftLlmOutput.model_json_schema(),
        )
        parsed = TrendProblemDraftLlmOutput.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        save_llm_job(
            db,
            kind="trend_problem",
            model=settings.gemini_model,
            request_params=request_params,
            response_json=None,
            status="failed",
            error_message=str(exc),
            created_by=user_id,
        )
        raise LlmFeatureError(str(exc)) from exc

    drafts = []
    seen_targets: set[tuple[int, int]] = set()
    for draft in parsed.drafts:
        key = (draft.test_id, draft.unit_id)
        meta = target_meta.get(key)
        if meta is None or key in seen_targets:
            continue  # not one of the requested (trend-having) targets, or a duplicate -> discard
        steps = sorted(h.step for h in draft.hints)
        if steps != [1, 2, 3]:
            continue  # spec: hints must be exactly 3 steps, discard otherwise
        seen_targets.add(key)

        format_id = draft.format_id if draft.format_id in valid_format_ids else meta["fallback_format_id"]
        difficulty = min(max(draft.difficulty, 1), 3)
        prerequisite_unit_ids = [uid for uid in draft.prerequisite_unit_ids if uid in meta["valid_prereq_ids"]]
        ordered_hints = sorted(draft.hints, key=lambda h: h.step)

        drafts.append(
            {
                "test_id": draft.test_id,
                "unit_id": draft.unit_id,
                "format_id": format_id,
                "difficulty": difficulty,
                "body": draft.body,
                "answer": draft.answer,
                "explanation": draft.explanation,
                "hints": [{"step": h.step, "body": h.body} for h in ordered_hints],
                "prerequisite_unit_ids": prerequisite_unit_ids,
            }
        )

    job = save_llm_job(
        db,
        kind="trend_problem",
        model=settings.gemini_model,
        request_params=request_params,
        response_json={"drafts": drafts},
        status="done",
        error_message=None,
        created_by=user_id,
    )
    return job, drafts
