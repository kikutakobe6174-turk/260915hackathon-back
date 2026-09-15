from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Worksheet(Base):
    __tablename__ = "worksheet"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("test.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(1), nullable=False)  # A | B | C
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    printed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WorksheetItem(Base):
    __tablename__ = "worksheet_item"
    __table_args__ = (UniqueConstraint("worksheet_id", "item_no", name="uq_worksheet_item_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    worksheet_id: Mapped[int] = mapped_column(ForeignKey("worksheet.id"), nullable=False)
    item_no: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "7" or "R-2"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problem.id"), nullable=False)
    is_return: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_item_id: Mapped[int | None] = mapped_column(ForeignKey("worksheet_item.id"), nullable=True)
