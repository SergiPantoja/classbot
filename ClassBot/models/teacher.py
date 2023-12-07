from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.user import User # avoid circular import
    from models.course import Course
    from models.teacher_classroom import Teacher_classroom
    from models.token import Token
    from models.student_token import Student_token
    from models.pending import Pending

# specialization of User table
class Teacher(Base):
    __tablename__ = 'teacher'

    # user_id is a foreign key to the user table, and primary key for this table
    id: Mapped[int] = mapped_column(ForeignKey('user.id'), primary_key=True)
    active_classroom_id: Mapped[Optional[int]] = mapped_column(ForeignKey('classroom.id'))

    # One-to-one specialization of user
    user: Mapped["User"] = relationship(back_populates='teacher')
    # One-to-many relationship with course
    courses: Mapped[Optional[List["Course"]]] = relationship(back_populates="teacher")
    # Many-to-many relationship with classroom
    classrooms: Mapped[Optional[List["Teacher_classroom"]]] = relationship(back_populates="teacher", cascade='all, delete-orphan')
    # one-to-many relationship with tokens created by the teacher (optional, dont
    # need to delete tokens when teacher is deleted)
    created_tokens: Mapped[Optional[List["Token"]]] = relationship(back_populates="teacher_creator")
    # Relationship tokens_given: One-to-many relationship with token (dont need 
    # to delete tokens when teacher is deleted)
    tokens_given: Mapped[Optional[List["Student_token"]]] = relationship(back_populates="given_by")
    # One-to-many relationship with pending
    direct_pendings: Mapped[Optional[List["Pending"]]] = relationship(back_populates="direct_pending_teacher", foreign_keys='Pending.teacher_id')
    approved_pendings: Mapped[Optional[List["Pending"]]] = relationship(back_populates="approved_by_teacher", foreign_keys='Pending.approved_by')
    
    def __repr__(self) -> str:
        return f'Teacher(id={self.id})'
    