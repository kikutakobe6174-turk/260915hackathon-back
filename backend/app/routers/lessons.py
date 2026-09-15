from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_db
from app.models import (
    AnswerSheet,
    Attempt,
    Lesson,
    School,
    Student,
    Test,
    Worksheet,
    WorksheetItem,
)
from app.schemas.answer_sheet import AnswerSheetListItem, AnswerSheetsCreateRequest
from app.schemas.lesson import LessonCreate, LessonOut
from app.services.lookup import get_or_404

router = APIRouter(tags=["lessons"])


@router.get("/lessons", response_model=list[LessonOut])
def list_lessons(test_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> list[LessonOut]:
    q = db.query(Lesson)
    if test_id is not None:
        q = q.filter(Lesson.test_id == test_id)
    lessons = q.order_by(Lesson.lesson_date.desc(), Lesson.id.desc()).all()
    return [LessonOut.model_validate(l) for l in lessons]


@router.post("/lessons", response_model=LessonOut, status_code=201)
def create_lesson(payload: LessonCreate, db: Session = Depends(get_db)) -> LessonOut:
    get_or_404(db, Test, payload.test_id, "テスト")

    lesson = Lesson(
        test_id=payload.test_id,
        lesson_date=payload.lesson_date,
        class_name=payload.class_name,
        round=payload.round,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return LessonOut.model_validate(lesson)


def _answer_sheet_list_items(db: Session, lesson_id: int) -> list[AnswerSheetListItem]:
    sheets = db.query(AnswerSheet).filter(AnswerSheet.lesson_id == lesson_id).order_by(AnswerSheet.id).all()

    students = {s.id: s for s in db.query(Student).all()}
    schools = {s.id: s.name for s in db.query(School).all()}
    worksheets = {w.id: w for w in db.query(Worksheet).all()}

    red_card_counts: dict[int, int] = {}
    for answer_sheet_id, cnt in (
        db.query(Attempt.answer_sheet_id, func.count())
        .filter(Attempt.red_card.is_(True))
        .group_by(Attempt.answer_sheet_id)
        .all()
    ):
        red_card_counts[answer_sheet_id] = cnt

    items = []
    for sheet in sheets:
        student = students.get(sheet.student_id)
        worksheet = worksheets.get(sheet.worksheet_id)
        items.append(
            AnswerSheetListItem(
                id=sheet.id,
                student_id=sheet.student_id,
                student_code=student.student_code if student else "",
                school_name=schools.get(student.school_id, "") if student else "",
                worksheet_id=sheet.worksheet_id,
                worksheet_level=worksheet.level if worksheet else "",
                status=sheet.status,
                red_card_count=red_card_counts.get(sheet.id, 0),
            )
        )
    return items


@router.get("/lessons/{lesson_id}/answer-sheets", response_model=list[AnswerSheetListItem])
def list_answer_sheets(lesson_id: int, db: Session = Depends(get_db)) -> list[AnswerSheetListItem]:
    get_or_404(db, Lesson, lesson_id, "授業回")
    return _answer_sheet_list_items(db, lesson_id)


@router.post("/lessons/{lesson_id}/answer-sheets", response_model=list[AnswerSheetListItem], status_code=201)
def create_answer_sheets(
    lesson_id: int, payload: AnswerSheetsCreateRequest, db: Session = Depends(get_db)
) -> list[AnswerSheetListItem]:
    lesson = get_or_404(db, Lesson, lesson_id, "授業回")

    existing_student_ids = {
        row.student_id
        for row in db.query(AnswerSheet.student_id).filter(AnswerSheet.lesson_id == lesson_id).all()
    }

    for assignment in payload.assignments:
        get_or_404(db, Student, assignment.student_id, "生徒")
        worksheet = get_or_404(db, Worksheet, assignment.worksheet_id, "冊子")
        if worksheet.test_id != lesson.test_id:
            raise AppError(
                code="VALIDATION_ERROR",
                message="この授業回のテストに属さない冊子です",
                status_code=400,
            )
        if assignment.student_id in existing_student_ids:
            continue

        db.add(
            AnswerSheet(
                student_id=assignment.student_id,
                lesson_id=lesson_id,
                worksheet_id=assignment.worksheet_id,
                status="empty",
                source="manual",
            )
        )
        existing_student_ids.add(assignment.student_id)

    db.commit()
    return _answer_sheet_list_items(db, lesson_id)
