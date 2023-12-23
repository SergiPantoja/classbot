import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.activity_type import Activity_type
    from models.practic_class_exercise import Practic_class_exercise

class Practic_class(Base):
    __tablename__ = 'practic_class'

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_type_id: Mapped[int] = mapped_column(ForeignKey('activity_type.id'))
    date: Mapped[datetime.date] = mapped_column(DateTime(timezone=True))

    # one-to-one relationship with activity_type
    activity_type: Mapped["Activity_type"] = relationship(back_populates='practic_class') # To delete practic classes, delete the associated activity types - delete the associated token_type
    # one-to-many relationship with practic_class_exercise (delete practic_class_exercise if practic_class is deleted)
    practic_class_exercise: Mapped["Practic_class_exercise"] = relationship(back_populates='practic_class', cascade='all, delete-orphan')

    __table_args__ = (
        # Unique constraint for activity_type_id
        UniqueConstraint('activity_type_id'),
    )

    def __repr__(self) -> str:
        return f'Practic_class(id={self.id}, activity_type_id={self.activity_type_id}, date={self.date})'
