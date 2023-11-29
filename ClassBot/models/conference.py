from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.classroom import Classroom # avoid circular import

class Conference(Base):
    __tablename__ = 'conference'

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classroom.id'))
    name: Mapped[str]
    date: Mapped[str]
    fileID: Mapped[Optional[str]] = mapped_column(default=None)

    # Many-to-one relationship with classroom
    classroom: Mapped["Classroom"] = relationship(back_populates='conferences')

    def __repr__(self) -> str:
        return f'Conference(id={self.id}, classroom_id={self.classroom_id}, name={self.name}, date={self.date}, fileID={self.fileID})'
