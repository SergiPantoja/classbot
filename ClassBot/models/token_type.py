from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.classroom import Classroom # avoid circular import
    from models.token import Token
    from models.pending import Pending
    from models.activity_type import Activity_type

class Token_type(Base):
    __tablename__ = 'token_type'

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[Optional[int]] = mapped_column(ForeignKey('classroom.id'))
    type: Mapped[str] = mapped_column(unique=True)
    hidden: Mapped[bool] = mapped_column(default=False)

    # Many-to-one relationship with classroom (Optional: default token types don't have a classroom)
    classroom: Mapped[Optional["Classroom"]] = relationship(back_populates='token_types')
    # One-to-many relationship with token
    tokens: Mapped[Optional[List["Token"]]] = relationship(back_populates='token_type', cascade='all, delete-orphan')
    # One-to-many relationship with pending
    pendings: Mapped[Optional[List["Pending"]]] = relationship(back_populates='token_type', cascade='all, delete-orphan')
    # one-to-one relationship with activity_type (delete activity_type if token_type is deleted)
    activity_type: Mapped[Optional["Activity_type"]] = relationship(back_populates='token_type', cascade='all, delete-orphan')

    __table_args__ = (
        # Unique constraint for course_id and type
        UniqueConstraint('classroom_id', 'type'),
    )

    def __repr__(self) -> str:
        return f'Token_type(id={self.id}, classroom_id={self.classroom_id}, type={self.type}, hidden={self.hidden})'
