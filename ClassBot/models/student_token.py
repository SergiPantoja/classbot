import datetime
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.student import Student # avoid circular import
    from models.token import Token
    from models.teacher import Teacher

class Student_token(Base):
    __tablename__ = 'student_token'

    student_id: Mapped[int] = mapped_column(ForeignKey('student.id'), primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey('token.id'), primary_key=True)
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey('teacher.id'))
    creation_date: Mapped[datetime.date] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student: Mapped["Student"] = relationship(back_populates="tokens")
    token: Mapped["Token"] = relationship(back_populates="students")
    # Relationship given_by: Many-to-one relationship with teacher (Optional:
    # some tokens are asignated by the system)
    given_by: Mapped[Optional["Teacher"]] = relationship(back_populates='tokens_given')

    def __repr__(self) -> str:
        return f'Student_token(student_id={self.student_id}, token_id={self.token_id}, teacher_id={self.teacher_id}, creation_date={self.creation_date})'
