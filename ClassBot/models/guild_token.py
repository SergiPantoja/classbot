from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.guild import Guild
    from models.token import Token

class Guild_token(Base):
    __tablename__ = 'guild_token'

    guild_id: Mapped[int] = mapped_column(ForeignKey('guild.id'), primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey('token.id'), primary_key=True)

    guild: Mapped["Guild"] = relationship(back_populates="tokens")
    token: Mapped["Token"] = relationship(back_populates="guilds")

    def __repr__(self) -> str:
        return f'guild_token(guild_id={self.guild_id}, token_id={self.token_id})'    
