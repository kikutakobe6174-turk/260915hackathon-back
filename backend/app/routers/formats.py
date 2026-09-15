from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import Format
from app.schemas.format import FormatCreate, FormatOut, FormatUpdate
from app.services.lookup import get_or_404

router = APIRouter(prefix="/formats", tags=["formats"])


@router.get("", response_model=list[FormatOut])
def list_formats(db: Session = Depends(get_db)) -> list[FormatOut]:
    formats = db.query(Format).order_by(Format.id).all()
    return [FormatOut.model_validate(f) for f in formats]


@router.post("", response_model=FormatOut, status_code=201)
def create_format(payload: FormatCreate, db: Session = Depends(get_db)) -> FormatOut:
    fmt = Format(name=payload.name)
    db.add(fmt)
    db.commit()
    db.refresh(fmt)
    return FormatOut.model_validate(fmt)


@router.put("/{format_id}", response_model=FormatOut)
def update_format(format_id: int, payload: FormatUpdate, db: Session = Depends(get_db)) -> FormatOut:
    fmt = get_or_404(db, Format, format_id, "形式")
    fmt.name = payload.name
    db.commit()
    db.refresh(fmt)
    return FormatOut.model_validate(fmt)


@router.delete("/{format_id}", status_code=204)
def delete_format(format_id: int, db: Session = Depends(get_db)) -> None:
    fmt = get_or_404(db, Format, format_id, "形式")
    db.delete(fmt)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            code="CONFLICT",
            message="この形式は他のデータから参照されているため削除できません",
            status_code=409,
        ) from exc
