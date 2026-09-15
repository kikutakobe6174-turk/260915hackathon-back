from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class School(Base):
    __tablename__ = "school"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
