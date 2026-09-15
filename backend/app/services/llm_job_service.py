from sqlalchemy.orm import Session

from app.models import LlmJob


def save_llm_job(
    db: Session,
    kind: str,
    model: str,
    request_params: dict,
    response_json: dict | None,
    status: str,
    error_message: str | None,
    created_by: int,
) -> LlmJob:
    """Persist an LLM_JOB row. request_params must never contain image bytes."""
    job = LlmJob(
        kind=kind,
        request_params=request_params,
        response_json=response_json,
        model=model,
        status=status,
        error_message=error_message,
        created_by=created_by,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
