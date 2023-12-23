from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.token_type import Token_type
    from models.activity import Activity
    from models.practic_class import Practic_class

class Activity_type(Base):
    __tablename__ = 'activity_type'

    id: Mapped[int] = mapped_column(primary_key=True)
    token_type_id: Mapped[int] = mapped_column(ForeignKey('token_type.id'))
    description: Mapped[Optional[str]] = mapped_column()
    guild_activity: Mapped[bool] = mapped_column(default=False)
    single_submission: Mapped[bool] = mapped_column(default=False)
    FileID: Mapped[Optional[str]] = mapped_column()

    # one-to-one relationship with token_type (delete token_type if activity_type is deleted)
    token_type: Mapped["Token_type"] = relationship(back_populates='activity_type')   # To delete activity types, delete the associated token types
    # one-to-many relationship with activity (delete activity if activity_type is deleted)
    activity: Mapped["Activity"] = relationship(back_populates='activity_type', cascade='all, delete-orphan')
    # one-to-one relationship with practic_class (delete practic_class if activity_type is deleted)
    practic_class: Mapped[Optional["Practic_class"]] = relationship(back_populates='activity_type', cascade='all, delete-orphan')

    __table_args__ = (
        # Unique constraint for token_type_id
        UniqueConstraint('token_type_id'),
    )

    def __repr__(self) -> str:
        return f'Activity_type(id={self.id}, token_type_id={self.token_type_id}, description={self.description}, guild_activity={self.guild_activity}, single_submission={self.single_submission}, FileID={self.FileID})'
