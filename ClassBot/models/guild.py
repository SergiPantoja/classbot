from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.classroom import Classroom

class Guild(Base):
    __tablename__ = 'guild'

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classroom.id'))

    # many-to-one relationship with classroom
    classroom: Mapped["Classroom"] = relationship(back_populates="guilds")

    # def __repr_(self) -> str:
