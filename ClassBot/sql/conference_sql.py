import datetime

from sqlalchemy import select

from models.conference import Conference
from sql import session


def get_conference(id: int) -> Conference | None:
    """ Returns a conference object with the given id. None if not found."""
    with session() as s:
        return s.query(Conference).filter(Conference.id == id).first()

def get_conferences_by_classroom(classroom_id: int) -> list[Conference]:
    """ Returns a list of conferences belonging to the given classroom. """
    with session() as s:
        return s.query(Conference).filter(Conference.classroom_id == classroom_id).all()


def add_conference(classroom_id: int, name: str, date: datetime, fileID: str = None) -> None:
    """ Adds a new conference to the database. """
    with session() as s:
        s.add(Conference(classroom_id=classroom_id, name=name, date=date, fileID=fileID))
        s.commit()
