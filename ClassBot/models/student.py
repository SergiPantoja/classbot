from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User # avoid circular import
    from models.student_classroom import Student_classroom


# specialization of User table
class Student(Base):
    __tablename__ = 'student'

    # user_id is a foreign key to the user table, and primary key for this table
    id: Mapped[int] = mapped_column(ForeignKey('user.id'), primary_key=True)

    # One-to-one specialization of user
    user: Mapped["User"] = relationship(back_populates='student')
    # Many-to-many relationship with classroom
    classrooms: Mapped[Optional[List["Student_classroom"]]] = relationship(back_populates="student", cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'Student(id={self.id})'