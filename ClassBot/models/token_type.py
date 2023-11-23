from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.course import Course # avoid circular import
    from models.token import Token

class Token_type(Base):
    __tablename__ = 'token_type'

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey('course.id'))
    type: Mapped[str] = mapped_column(unique=True)
    hidden: Mapped[bool] = mapped_column(default=False)

    # Many-to-one relationship with course (Optional: default token types don't have a course)
    course: Mapped[Optional["Course"]] = relationship(back_populates='token_types')
    # One-to-many relationship with token
    tokens: Mapped[Optional[List["Token"]]] = relationship(back_populates='token_type', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'Token_type(id={self.id}, course_id={self.course_id}, type={self.type}, hidden={self.hidden})'
