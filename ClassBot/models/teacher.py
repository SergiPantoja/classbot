from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User # avoid circular import
    from models.course import Course
    from models.teacher_classroom import Teacher_classroom


# specialization of User table
class Teacher(Base):
    __tablename__ = 'teacher'

    # user_id is a foreign key to the user table, and primary key for this table
    id: Mapped[int] = mapped_column(ForeignKey('user.id'), primary_key=True)

    # One-to-one specialization of user
    user: Mapped["User"] = relationship(back_populates='teacher')
    # One-to-many relationship with course
    courses: Mapped[Optional[List["Course"]]] = relationship(back_populates='teacher')
    # Many-to-many relationship with classroom
    classrooms: Mapped[Optional[List["Teacher_classroom"]]] = relationship(back_populates="teacher", cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'Teacher(id={self.id})'