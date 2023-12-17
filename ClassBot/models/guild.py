from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.classroom import Classroom
    from models.pending import Pending
    from models.student_guild import Student_guild
    from models.guild_token import Guild_token

class Guild(Base):
    __tablename__ = 'guild'

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classroom.id'))
    name: Mapped[str]

    # many-to-one relationship with classroom
    classroom: Mapped["Classroom"] = relationship(back_populates="guilds")
    # one-to-many relationship with pending
    pendings: Mapped[Optional[List["Pending"]]] = relationship(back_populates="guild", cascade="all, delete-orphan")
    # many-to-many relationship with student
    students: Mapped[Optional[List["Student_guild"]]] = relationship(back_populates="guild", cascade="all, delete-orphan")
    # many-to-many relationship with token
    tokens: Mapped[Optional[List["Guild_token"]]] = relationship(back_populates="guild", cascade="all, delete-orphan")

    # def __repr_(self) -> str:
