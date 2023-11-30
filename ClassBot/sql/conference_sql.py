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

def update_conference_name(id: int, name: str) -> None:
    """ Updates the name of the conference with the given id. """
    with session() as s:
        s.query(Conference).filter(Conference.id == id).update({"name": name})
        s.commit()

def update_conference_date(id: int, date: datetime) -> None:
    """ Updates the date of the conference with the given id. """
    with session() as s:
        s.query(Conference).filter(Conference.id == id).update({"date": date})
        s.commit()

def update_conference_fileID(id: int, fileID: str) -> None:
    """ Updates the fileID of the conference with the given id. """
    with session() as s:
        s.query(Conference).filter(Conference.id == id).update({"fileID": fileID})
        s.commit()

def delete_conference(id: int) -> None:
    """ Deletes the conference from the database. """
    with session() as s:
        # get conference
        conference = s.execute(select(Conference).where(Conference.id == id)).scalar_one()
        # delete conference
        s.delete(conference)
        s.commit()
