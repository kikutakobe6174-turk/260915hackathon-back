from datetime import date as date_

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Lesson(Base):
    __tablename__ = "lesson"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("test.id"), nullable=False)
    lesson_date: Mapped[date_] = mapped_column(Date, nullable=False)
    class_name: Mapped[str] = mapped_column(String(50), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
