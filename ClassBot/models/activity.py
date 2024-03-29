import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.activity_type import Activity_type
    from models.token import Token
    from models.practic_class_exercise import Practic_class_exercise

class Activity(Base):
    __tablename__ = 'activity'

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_type_id: Mapped[int] = mapped_column(ForeignKey('activity_type.id'))
    token_id: Mapped[int] = mapped_column(ForeignKey('token.id'))
    FileID: Mapped[Optional[str]] = mapped_column()
    submission_deadline: Mapped[Optional[datetime.date]] = mapped_column(DateTime(timezone=True), default=None)

    # many-to-one relationship with activity_type 
    activity_type: Mapped["Activity_type"] = relationship(back_populates='activity')
    # one-to-one relationship with token    (doesnt delete token in cascade to keep record of credits)
    token: Mapped["Token"] = relationship(back_populates='activity')    # To delete activities, delete the associated token
    # one-to-one relationship with practic_class_exercise (delete practic_class_exercise if activity is deleted)
    practic_class_exercise: Mapped[Optional["Practic_class_exercise"]] = relationship(back_populates='activity', cascade='all, delete-orphan')

    __table_args__ = (
        # Unique constraint for token_id
        UniqueConstraint('token_id'),
    )

    def __repr__(self) -> str:
        return f'Activity(id={self.id}, activity_type_id={self.activity_type_id}, token_id={self.token_id}, FileID={self.FileID})'
