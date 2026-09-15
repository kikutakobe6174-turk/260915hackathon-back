from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Student(Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)
    level: Mapped[str] = mapped_column(String(1), nullable=False)  # A | B | C
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
