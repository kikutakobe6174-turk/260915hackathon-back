from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import School, Student
from app.schemas.common import ImportResult, ImportRowError
from app.schemas.student import StudentCreate, StudentImportRequest, StudentOut, StudentUpdate
from app.services.lookup import get_or_404

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=list[StudentOut])
def list_students(
    school_id: int | None = Query(default=None),
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[StudentOut]:
    q = db.query(Student)
    if school_id is not None:
        q = q.filter(Student.school_id == school_id)
    if active is not None:
        q = q.filter(Student.active == active)
    students = q.order_by(Student.id).all()
    return [StudentOut.model_validate(s) for s in students]


@router.post("", response_model=StudentOut, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)) -> StudentOut:
    get_or_404(db, School, payload.school_id, "学校")

    if db.query(Student).filter(Student.student_code == payload.student_code).first():
        raise AppError(code="DUPLICATE", message="この生徒番号は既に使われています", status_code=409)

    student = Student(
        student_code=payload.student_code,
        school_id=payload.school_id,
        grade=payload.grade,
        level=payload.level,
        active=payload.active,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentOut.model_validate(student)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db)) -> StudentOut:
    student = get_or_404(db, Student, student_id, "生徒")
    get_or_404(db, School, payload.school_id, "学校")

    duplicate = (
        db.query(Student)
        .filter(Student.student_code == payload.student_code, Student.id != student_id)
        .first()
    )
    if duplicate:
        raise AppError(code="DUPLICATE", message="この生徒番号は既に使われています", status_code=409)

    student.student_code = payload.student_code
    student.school_id = payload.school_id
    student.grade = payload.grade
    student.level = payload.level
    student.active = payload.active
    db.commit()
    db.refresh(student)
    return StudentOut.model_validate(student)


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db)) -> None:
    student = get_or_404(db, Student, student_id, "生徒")
    db.delete(student)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            code="CONFLICT",
            message="この生徒は他のデータから参照されているため削除できません",
            status_code=409,
        ) from exc


@router.post("/import", response_model=ImportResult)
def import_students(payload: StudentImportRequest, db: Session = Depends(get_db)) -> ImportResult:
    schools_by_name = {s.name: s.id for s in db.query(School).all()}
    existing_codes = {s.student_code for s in db.query(Student.student_code).all()}

    errors: list[ImportRowError] = []
    created = 0
    seen_codes: set[str] = set()

    for i, row in enumerate(payload.rows):
        code = row.student_code.strip()
        if not code:
            errors.append(ImportRowError(row=i, message="生徒番号が空です"))
            continue
        if code in existing_codes or code in seen_codes:
            errors.append(ImportRowError(row=i, message=f"生徒番号 {code} は既に使われています"))
            continue
        school_id = schools_by_name.get(row.school_name.strip())
        if school_id is None:
            errors.append(ImportRowError(row=i, message=f"学校「{row.school_name}」が見つかりません"))
            continue

        db.add(Student(student_code=code, school_id=school_id, grade=row.grade, level=row.level, active=True))
        seen_codes.add(code)
        created += 1

    db.commit()
    return ImportResult(created=created, errors=errors)
