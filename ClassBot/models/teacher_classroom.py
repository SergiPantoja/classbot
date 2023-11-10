from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from ClassBot.models.base import Base

if TYPE_CHECKING:
    from ClassBot.models.teacher import Teacher # avoid circular import
    from ClassBot.models.classroom import Classroom


class teacher_classroom(Base):
    """ association table between teacher and classroom """
    __tablename__ = 'teacher_classroom'

    teacher_id: Mapped[int] = mapped_column(ForeignKey('teacher.id'), primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classroom.id'), primary_key=True)

    teacher: Mapped["Teacher"] = relationship(back_populates="classrooms")
    classroom: Mapped["Classroom"] = relationship(back_populates="teachers")

    def __repr__(self) -> str:
        return f'teacher_classroom(teacher_id={self.teacher_id}, classroom_id={self.classroom_id})'
