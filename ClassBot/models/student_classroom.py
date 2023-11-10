from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.student import Student # avoid circular import
    from models.classroom import Classroom


class Student_classroom(Base):
    """ association table between student and classroom """
    __tablename__ = 'student_classroom'

    student_id: Mapped[int] = mapped_column(ForeignKey('student.id'), primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classroom.id'), primary_key=True)

    student: Mapped["Student"] = relationship(back_populates="classrooms")
    classroom: Mapped["Classroom"] = relationship(back_populates="teachers")

    def __repr__(self) -> str:
        return f'student_classroom(teacher_id={self.student_id}, classroom_id={self.classroom_id})'
