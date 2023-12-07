from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.classroom import Classroom
    from models.pending import Pending

class Guild(Base):
    __tablename__ = 'guild'

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classroom.id'))

    # many-to-one relationship with classroom
    classroom: Mapped["Classroom"] = relationship(back_populates="guilds")
    # one-to-many relationship with pending
    pendings: Mapped[Optional[List["Pending"]]] = relationship(back_populates="guild", cascade="all, delete-orphan")

    # def __repr_(self) -> str:
