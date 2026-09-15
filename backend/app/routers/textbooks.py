from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import Textbook
from app.schemas.textbook import TextbookCreate, TextbookOut, TextbookUpdate
from app.services.lookup import get_or_404

router = APIRouter(prefix="/textbooks", tags=["textbooks"])


@router.get("", response_model=list[TextbookOut])
def list_textbooks(db: Session = Depends(get_db)) -> list[TextbookOut]:
    textbooks = db.query(Textbook).order_by(Textbook.id).all()
    return [TextbookOut.model_validate(t) for t in textbooks]


@router.post("", response_model=TextbookOut, status_code=201)
def create_textbook(payload: TextbookCreate, db: Session = Depends(get_db)) -> TextbookOut:
    textbook = Textbook(publisher=payload.publisher, title=payload.title, subject=payload.subject)
    db.add(textbook)
    db.commit()
    db.refresh(textbook)
    return TextbookOut.model_validate(textbook)


@router.put("/{textbook_id}", response_model=TextbookOut)
def update_textbook(textbook_id: int, payload: TextbookUpdate, db: Session = Depends(get_db)) -> TextbookOut:
    textbook = get_or_404(db, Textbook, textbook_id, "教科書")
    textbook.publisher = payload.publisher
    textbook.title = payload.title
    textbook.subject = payload.subject
    db.commit()
    db.refresh(textbook)
    return TextbookOut.model_validate(textbook)


@router.delete("/{textbook_id}", status_code=204)
def delete_textbook(textbook_id: int, db: Session = Depends(get_db)) -> None:
    textbook = get_or_404(db, Textbook, textbook_id, "教科書")
    db.delete(textbook)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            code="CONFLICT",
            message="この教科書は他のデータから参照されているため削除できません",
            status_code=409,
        ) from exc
