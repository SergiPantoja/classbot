from typing import TYPE_CHECKING, Optional
from sqlalchemy import DATE
from sqlalchemy.orm import mapped_column, Mapped, relationship

from ClassBot.models.base import Base

if TYPE_CHECKING:
    from ClassBot.models.student import Student # avoid circular import
    from ClassBot.models.teacher import Teacher

class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)
    fullname: Mapped[str]
    telegram_chatid: Mapped[str]
    creation_date: Mapped[DATE] = mapped_column(default=DATE.today())

    student: Mapped[Optional["Student"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    teacher: Mapped[Optional["Teacher"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f'User(id={self.id}, fullname={self.fullname}, telegram_chatid={self.telegram_chatid}, creation_date={self.creation_date})'
