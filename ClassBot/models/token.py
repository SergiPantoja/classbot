import datetime
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.token_type import Token_type # avoid circular import
    from models.course import Course
    from models.teacher import Teacher
    from models.student_token import Student_token

class Token(Base):
    __tablename__ = 'token'

    id: Mapped[int] = mapped_column(primary_key=True)
    token_type_id: Mapped[int] = mapped_column(ForeignKey('token_type.id'))
    course_id: Mapped[int] = mapped_column(ForeignKey('course.id'))
    teacher_creator_id: Mapped[Optional[int]] = mapped_column(ForeignKey('teacher.id'))
    name: Mapped[str]
    value: Mapped[int]
    description: Mapped[Optional[str]] = mapped_column(default=None)
    creation_date: Mapped[datetime.date] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    automatic: Mapped[bool] = mapped_column(default=False)
    image_url: Mapped[Optional[str]] = mapped_column(default=None)  # only for specific token types

    # Many-to-one relationship with token_type
    token_type: Mapped["Token_type"] = relationship(back_populates='tokens')
    # Many-to-one relationship with course
    course: Mapped["Course"] = relationship(back_populates='tokens')
    # Many-to-one relationship with teacher (Optional: some tokens are created by the system)
    teacher_creator: Mapped[Optional["Teacher"]] = relationship(back_populates='tokens')
    # Many-to-many relationship with student
    students: Mapped[Optional[List["Student_token"]]] = relationship(back_populates='tokens', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'Token(id={self.id}, token_type_id={self.token_type_id}, course_id={self.course_id}, teacher_creator_id={self.teacher_creator_id}, name={self.name}, value={self.value}, description={self.description}, creation_date={self.creation_date}, automatic={self.automatic}, image_url={self.image_url})'
