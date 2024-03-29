import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.student import Student
    from models.classroom import Classroom
    from models.token_type import Token_type
    from models.teacher import Teacher
    from models.guild import Guild
    from models.token import Token

class Pending(Base):
    __tablename__ = "pending"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('student.id'))
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classroom.id'))
    token_type_id: Mapped[int] = mapped_column(ForeignKey('token_type.id'))
    token_id: Mapped[Optional[int]] = mapped_column(ForeignKey('token.id', ondelete='SET NULL'))
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey('teacher.id', ondelete='SET NULL'))
    guild_id: Mapped[Optional[int]] = mapped_column(ForeignKey('guild.id'))
    status: Mapped[str] = mapped_column(default='pending') # PENDING, APPROVED, REJECTED
    creation_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
        )
    approved_date: Mapped[Optional[datetime.date]] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey('teacher.id', ondelete='SET NULL'))
    text: Mapped[Optional[str]] = mapped_column()
    FileID: Mapped[Optional[str]] = mapped_column(default=None)
    explanation: Mapped[Optional[str]] = mapped_column(default=None)    # explanation for rejection
    # if teacher asks for more info, None if not. Values: "PENDING", "SENT". Info is stored in the text column.
    more_info: Mapped[Optional[str]] = mapped_column(default=None) 

    # many-to-one relationship with student
    student: Mapped["Student"] = relationship(back_populates="pendings")
    # many-to-one relationship with classroom
    classroom: Mapped["Classroom"] = relationship(back_populates="pendings")
    # many-to-one relationship with token_type
    token_type: Mapped["Token_type"] = relationship(back_populates="pendings")
    # many-to-one relationship with teacher (for direct pending)
    direct_pending_teacher: Mapped[Optional["Teacher"]] = relationship(back_populates="direct_pendings", foreign_keys=[teacher_id], passive_deletes=True)
    # many-to-one relationship with teacher (for approved pending)
    approved_by_teacher: Mapped[Optional["Teacher"]] = relationship(back_populates="approved_pendings", foreign_keys=[approved_by], passive_deletes=True)
    # many-to-one relationship with guild
    guild: Mapped[Optional["Guild"]] = relationship(back_populates="pendings")
    # Many-to-one relationship with token
    token: Mapped[Optional["Token"]] = relationship(back_populates="related_pendings")
    

    def __repr__(self) -> str:
        return f'Pending(id={self.id}, student_id={self.student_id}, classroom_id={self.classroom_id}, token_type_id={self.token_type_id}, token_id={self.token_id}, teacher_id={self.teacher_id}, guild_id={self.guild_id}, status={self.status}, creation_date={self.creation_date}, approved_date={self.approved_date}, approved_by={self.approved_by}, text={self.text}, FileID={self.FileID}, explanation={self.explanation}, more_info={self.more_info})'
