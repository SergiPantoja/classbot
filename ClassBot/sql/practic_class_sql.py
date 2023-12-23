import datetime

from sqlalchemy import select

from models.practic_class import Practic_class
from sql import session
import sql.activity_type_sql as activity_type_sql


def get_practic_class(id: int) -> Practic_class | None:
    """ Returns a practic_class object with the given id. None if not found."""
    with session() as s:
        return s.query(Practic_class).filter(Practic_class.id == id).first()
    
def get_practic_class_by_name(name: str, classroom_id: int) -> Practic_class | None:
    """
    Returns the first practic_class object with the activity_type_id of the activity_type (token_type)
    with the given name and classroom_id. None if not found.
    Since the activity_type_id is unique, this function will return only one object.
    And since the combination of type and classroom_id is unique, there will be only one token_type.
    If the token_type is not found, then the activity_type is not found either.
    """
    activity_type = activity_type_sql.get_activity_type_by_type(name, classroom_id)
    if activity_type is None:
        return None
    with session() as s:
        return s.query(Practic_class).filter(Practic_class.activity_type_id == activity_type.id).first()

def get_practic_class_by_activity_type_id(activity_type_id: int) -> Practic_class | None:
    """ Returns the first practic_class object with the given activity_type_id. None if not found.
        Since the activity_type_id is unique, this function will return only one object."""
    with session() as s:
        return s.query(Practic_class).filter(Practic_class.activity_type_id == activity_type_id).first()

def get_practic_classes(classroom_id: int, include_hidden: bool = False) -> list[Practic_class]:
    """ Return a list of practic_class objects with the activity_type_id of the activity_types
        with the given classroom_id. If include_hidden is True, then also include hidden practic_classes.
        Include hidden should be set to True in the Practic Class menus since these are created hidden by default.
    """
    activity_types = activity_type_sql.get_activity_types(classroom_id, include_hidden)
    with session() as s:
        return s.query(Practic_class).filter(Practic_class.activity_type_id.in_([activity_type.id for activity_type in activity_types])).all()
    
def add_practic_class(
        date: datetime,
        name: str,
        classroom_id: int,
        hidden: bool = True,            # Practic classes are hidden by default
        description: str = None,
        guild_activity: bool = False,
        single_submission: bool = True, # Practic classes are single submission
        FileID: str = None,
    ):
    """ Adds a new practic_class to the database. """
    with session() as s:
        activity_type_sql.add_activity_type(
            name,
            classroom_id,
            hidden,
            description,
            guild_activity,
            single_submission,
            FileID,
        )
        activity_type = activity_type_sql.get_activity_type_by_type(name, classroom_id)
        s.add(Practic_class(
            activity_type_id=activity_type.id,
            date=date,
        ))
        s.commit()

def update_date(id: int, date: datetime):
    """ Updates the date of the practic_class with the given id. """
    with session() as s:
        s.query(Practic_class).filter(Practic_class.id == id).update({"date": date})
        s.commit()

def update_description(id: int, description: str):
    """ Updates the description of the activity_type associated with this practic_class. """
    with session() as s:
        practic_class = s.query(Practic_class).filter(Practic_class.id == id).first()
        activity_type_sql.update_description(practic_class.activity_type_id, description)
        s.commit()

def update_file(id: int, FileID: str):
    """ Updates the FileID of the activity_type associated with this practic_class. """
    with session() as s:
        practic_class = s.query(Practic_class).filter(Practic_class.id == id).first()
        activity_type_sql.update_file(practic_class.activity_type_id, FileID)
        s.commit()
