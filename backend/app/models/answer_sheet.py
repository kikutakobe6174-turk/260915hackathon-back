from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AnswerSheet(Base):
    __tablename__ = "answer_sheet"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lesson.id"), nullable=False)
    worksheet_id: Mapped[int] = mapped_column(ForeignKey("worksheet.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="empty")
    # empty | in_progress | llm_draft | confirmed
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="manual")  # manual | llm
    llm_job_id: Mapped[int | None] = mapped_column(ForeignKey("llm_job.id"), nullable=True)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Attempt(Base):
    __tablename__ = "attempt"
    __table_args__ = (
        UniqueConstraint("answer_sheet_id", "worksheet_item_id", name="uq_attempt_sheet_item"),
        CheckConstraint("hint_step BETWEEN 0 AND 3", name="ck_attempt_hint_step"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_sheet_id: Mapped[int] = mapped_column(ForeignKey("answer_sheet.id"), nullable=False)
    worksheet_item_id: Mapped[int] = mapped_column(ForeignKey("worksheet_item.id"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hint_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    went_return: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    red_card: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
