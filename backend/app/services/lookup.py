from sqlalchemy.orm import Session

from app.core.errors import AppError


def get_or_404(db: Session, model, obj_id: int, entity_name: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise AppError(code="NOT_FOUND", message=f"{entity_name}が見つかりません", status_code=404)
    return obj
