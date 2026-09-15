from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import Textbook, Unit
from app.schemas.common import ImportResult, ImportRowError
from app.schemas.unit import UnitCreate, UnitImportRequest, UnitOut, UnitUpdate
from app.services.lookup import get_or_404

router = APIRouter(tags=["units"])


@router.get("/textbooks/{textbook_id}/units", response_model=list[UnitOut])
def list_units(textbook_id: int, db: Session = Depends(get_db)) -> list[UnitOut]:
    get_or_404(db, Textbook, textbook_id, "教科書")
    units = db.query(Unit).filter(Unit.textbook_id == textbook_id).order_by(Unit.order_no).all()
    return [UnitOut.model_validate(u) for u in units]


@router.post("/textbooks/{textbook_id}/units", response_model=UnitOut, status_code=201)
def create_unit(textbook_id: int, payload: UnitCreate, db: Session = Depends(get_db)) -> UnitOut:
    get_or_404(db, Textbook, textbook_id, "教科書")
    unit = Unit(textbook_id=textbook_id, name=payload.name, order_no=payload.order_no)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return UnitOut.model_validate(unit)


@router.put("/units/{unit_id}", response_model=UnitOut)
def update_unit(unit_id: int, payload: UnitUpdate, db: Session = Depends(get_db)) -> UnitOut:
    unit = get_or_404(db, Unit, unit_id, "単元")
    unit.name = payload.name
    unit.order_no = payload.order_no
    db.commit()
    db.refresh(unit)
    return UnitOut.model_validate(unit)


@router.delete("/units/{unit_id}", status_code=204)
def delete_unit(unit_id: int, db: Session = Depends(get_db)) -> None:
    unit = get_or_404(db, Unit, unit_id, "単元")
    db.delete(unit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            code="CONFLICT",
            message="この単元は他のデータから参照されているため削除できません",
            status_code=409,
        ) from exc


@router.post("/textbooks/{textbook_id}/units/import", response_model=ImportResult)
def import_units(textbook_id: int, payload: UnitImportRequest, db: Session = Depends(get_db)) -> ImportResult:
    get_or_404(db, Textbook, textbook_id, "教科書")

    errors: list[ImportRowError] = []
    created = 0
    for i, row in enumerate(payload.rows):
        if not row.name.strip():
            errors.append(ImportRowError(row=i, message="単元名が空です"))
            continue
        db.add(Unit(textbook_id=textbook_id, name=row.name.strip(), order_no=row.order_no))
        created += 1

    db.commit()
    return ImportResult(created=created, errors=errors)
