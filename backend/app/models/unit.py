from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Unit(Base):
    __tablename__ = "unit"

    id: Mapped[int] = mapped_column(primary_key=True)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbook.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
