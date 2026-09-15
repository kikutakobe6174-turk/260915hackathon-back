from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Test(Base):
    __tablename__ = "test"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbook.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)
    term: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # past | target
    image_discarded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TestScope(Base):
    __tablename__ = "test_scope"

    test_id: Mapped[int] = mapped_column(ForeignKey("test.id"), primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), primary_key=True)


class TestTrend(Base):
    __tablename__ = "test_trend"
    __table_args__ = (CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_test_trend_difficulty"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("test.id"), nullable=False)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("unit.id"), nullable=True)
    format_id: Mapped[int] = mapped_column(ForeignKey("format.id"), nullable=False)
    question_no: Mapped[str] = mapped_column(String(20), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # manual | llm
    llm_job_id: Mapped[int | None] = mapped_column(ForeignKey("llm_job.id"), nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
