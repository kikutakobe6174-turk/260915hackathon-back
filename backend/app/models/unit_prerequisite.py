from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UnitPrerequisite(Base):
    __tablename__ = "unit_prerequisite"

    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), primary_key=True)
    prerequisite_unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), primary_key=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # manual | llm
    llm_job_id: Mapped[int | None] = mapped_column(ForeignKey("llm_job.id"), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
