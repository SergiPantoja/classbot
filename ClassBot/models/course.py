from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from ClassBot.models.base import Base

if TYPE_CHECKING:
    from ClassBot.models.teacher import Teacher # avoid circular import
    from ClassBot.models.classroom import Classroom

class Course(Base):
    __tablename__ = 'course'

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey('teacher.id'))
    name: Mapped[str]

    # One-to-one relationship with teacher
    teacher: Mapped["Teacher"] = relationship(back_populates='course')
    # One-to-many relationship with classroom
    classrooms: Mapped[Optional[List["Classroom"]]] = relationship(back_populates='course', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'Course(id={self.id}, teacher_id={self.teacher_id}, name={self.name})'
