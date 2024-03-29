from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.course import Course # avoid circular import
    from models.teacher_classroom import Teacher_classroom
    from models.student_classroom import Student_classroom
    from models.conference import Conference
    from models.guild import Guild
    from models.pending import Pending
    from models.token_type import Token_type
    from models.token import Token

class Classroom(Base):
    __tablename__ = 'classroom'

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey('course.id'))
    name: Mapped[str]
    teacher_auth: Mapped[str] = mapped_column(unique=True)  
    student_auth: Mapped[str] = mapped_column(unique=True)
    teacher_notification_channel: Mapped[Optional[str]]

    # Many-to-one relationship with course
    course: Mapped["Course"] = relationship(back_populates='classrooms')
    # Many-to-many relationship with teacher
    teachers: Mapped[Optional[List["Teacher_classroom"]]] = relationship(back_populates="classroom", cascade="all, delete-orphan")
    # Many-to-many relationship with student
    students: Mapped[Optional[List["Student_classroom"]]] = relationship(back_populates="classroom", cascade="all, delete-orphan")
    # one-to-many relationship with conference
    conferences: Mapped[Optional[List["Conference"]]] = relationship(back_populates="classroom", cascade="all, delete-orphan")
    # one-to-many relationship with guild
    guilds: Mapped[Optional[List["Guild"]]] = relationship(back_populates="classroom", cascade="all, delete-orphan")
    # one-to-many relationship with pending
    pendings: Mapped[Optional[List["Pending"]]] = relationship(back_populates="classroom", cascade="all, delete-orphan")
    # One-to-many relationship with token_type
    token_types: Mapped[Optional[List["Token_type"]]] = relationship(back_populates='classroom', cascade='all, delete-orphan')
    # One-to-many relationship with token
    tokens: Mapped[Optional[List["Token"]]] = relationship(back_populates='classroom', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'Classroom(id={self.id}, course_id={self.course_id}, name={self.name}, teacher_auth={self.teacher_auth}, student_auth={self.student_auth})'
