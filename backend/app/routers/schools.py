from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import School
from app.schemas.school import SchoolCreate, SchoolOut, SchoolUpdate
from app.services.lookup import get_or_404

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("", response_model=list[SchoolOut])
def list_schools(db: Session = Depends(get_db)) -> list[SchoolOut]:
    schools = db.query(School).order_by(School.id).all()
    return [SchoolOut.model_validate(s) for s in schools]


@router.post("", response_model=SchoolOut, status_code=201)
def create_school(payload: SchoolCreate, db: Session = Depends(get_db)) -> SchoolOut:
    school = School(name=payload.name)
    db.add(school)
    db.commit()
    db.refresh(school)
    return SchoolOut.model_validate(school)


@router.put("/{school_id}", response_model=SchoolOut)
def update_school(school_id: int, payload: SchoolUpdate, db: Session = Depends(get_db)) -> SchoolOut:
    school = get_or_404(db, School, school_id, "学校")
    school.name = payload.name
    db.commit()
    db.refresh(school)
    return SchoolOut.model_validate(school)


@router.delete("/{school_id}", status_code=204)
def delete_school(school_id: int, db: Session = Depends(get_db)) -> None:
    school = get_or_404(db, School, school_id, "学校")
    db.delete(school)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            code="CONFLICT",
            message="この学校は他のデータから参照されているため削除できません",
            status_code=409,
        ) from exc
