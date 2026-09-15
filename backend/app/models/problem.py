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


class Problem(Base):
    __tablename__ = "problem"
    __table_args__ = (CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_problem_difficulty"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), nullable=False)
    format_id: Mapped[int] = mapped_column(ForeignKey("format.id"), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_return: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft")  # draft | reviewed
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # manual | llm
    llm_job_id: Mapped[int | None] = mapped_column(ForeignKey("llm_job.id"), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Hint(Base):
    __tablename__ = "hint"
    __table_args__ = (
        UniqueConstraint("problem_id", "step", name="uq_hint_problem_step"),
        CheckConstraint("step BETWEEN 1 AND 3", name="ck_hint_step"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problem.id"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class ProblemPrerequisite(Base):
    __tablename__ = "problem_prerequisite"

    problem_id: Mapped[int] = mapped_column(ForeignKey("problem.id"), primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), primary_key=True)
