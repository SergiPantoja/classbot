import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.guild import Guild
    from models.token import Token
    from models.teacher import Teacher

class Guild_token(Base):
    __tablename__ = 'guild_token'

    guild_id: Mapped[int] = mapped_column(ForeignKey('guild.id'), primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey('token.id'), primary_key=True)
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey('teacher.id'))
    value: Mapped[int]
    creation_date: Mapped[datetime.date] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    guild: Mapped["Guild"] = relationship(back_populates="tokens")
    token: Mapped["Token"] = relationship(back_populates="guilds")
    # Relationship given_by: Many-to-one relationship with teacher (Optional:
    # some tokens are asignated by the system)
    guild_tokens_given_by: Mapped[Optional["Teacher"]] = relationship(back_populates='guild_tokens_given')

    def __repr__(self) -> str:
        return f'Guild_token(guild_id={self.guild_id}, token_id={self.token_id}, teacher_id={self.teacher_id}, value={self.value}, creation_date={self.creation_date})'
