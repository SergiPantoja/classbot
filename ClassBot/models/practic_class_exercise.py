import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.practic_class import Practic_class
    from models.activity import Activity

class Practic_class_exercise(Base):
    __tablename__ = 'practic_class_exercise'

    id: Mapped[int] = mapped_column(primary_key=True)
    practic_class_id: Mapped[int] = mapped_column(ForeignKey('practic_class.id'))
    activity_id: Mapped[int] = mapped_column(ForeignKey('activity.id'))
    value: Mapped[int] = mapped_column()
    partial_credits_allowed: Mapped[bool] = mapped_column(default=False)

    # many-to-one relationship with practic_class
    practic_class: Mapped["Practic_class"] = relationship(back_populates='practic_class_exercise')
    # one-to-one relationship with activity
    activity: Mapped["Activity"] = relationship(back_populates='practic_class_exercise') # To delete practic class exercises, delete the associated activities - delete the associated tokens

    __table_args__ = (
        # Unique constraint for activity_id
        UniqueConstraint('activity_id'),
    )

    def __repr__(self) -> str:
        return f'Practic_class_exercise(id={self.id}, practic_class_id={self.practic_class_id}, activity_id={self.activity_id}, value={self.value}, partial_credits_allowed={self.partial_credits_allowed})'
