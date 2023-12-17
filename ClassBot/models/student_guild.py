from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.student import Student
    from models.guild import Guild

class Student_guild(Base):
    __tablename__ = 'student_guild'

    student_id: Mapped[int] = mapped_column(ForeignKey('student.id'), primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey('guild.id'), primary_key=True)

    student: Mapped["Student"] = relationship(back_populates="guilds")
    guild: Mapped["Guild"] = relationship(back_populates="students")

    def __repr__(self) -> str:
        return f'student_guild(student_id={self.student_id}, guild_id={self.guild_id})'
