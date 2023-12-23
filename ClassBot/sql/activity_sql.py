import datetime

from sqlalchemy import select

from models.activity import Activity
from sql import session
import sql.token_sql as token_sql
import sql.activity_type_sql as activity_type_sql


def get_activity(id: int) -> Activity | None:
    """ Returns an activity object with the given id. None if not found."""
    with session() as s:
        return s.query(Activity).filter(Activity.id == id).first()
    
def get_activity_by_token_id(token_id: int) -> Activity | None:
    """ Returns an activity object with the given token_id. None if not found."""
    with session() as s:
        return s.query(Activity).filter(Activity.token_id == token_id).first()

def get_activities_by_activity_type_id(activity_type_id: int) -> list[Activity]:
    """ Returns a list of activity objects with the given activity_type_id."""
    with session() as s:
        return s.query(Activity).filter(Activity.activity_type_id == activity_type_id).all()

def add_activity(
        activity_type_id: int, 
        classroom_id: int,
        name: str,
        description: str = None,
        FileID: str = None,
        deadline: datetime = None,    
    ):
    """ Adds a new activity to the database. """
    with session() as s:
        token_type_id = activity_type_sql.get_activity_type(activity_type_id).token_type_id
        token_sql.add_token(name, token_type_id, classroom_id, description=description)
        token_id = token_sql.get_last_token().id
        s.add(Activity(
            activity_type_id=activity_type_id,
            token_id=token_id,
            FileID=FileID,
            submission_deadline=deadline,
        ))
        s.commit()

def update_name(id: int, name: str):
    """ Updates the name of the activity with the given id. """
    with session() as s:
        activity = s.query(Activity).filter(Activity.id == id).first()
        token_sql.update_name(activity.token_id, name)
        s.commit()

def update_description(id: int, description: str):
    """ Updates the description of the activity with the given id. """
    with session() as s:
        activity = s.query(Activity).filter(Activity.id == id).first()
        token_sql.update_description(activity.token_id, description)
        s.commit()

def update_file(id: int, FileID: str):
    """ Updates the FileID of the activity with the given id. """
    with session() as s:
        s.query(Activity).filter(Activity.id == id).update({Activity.FileID: FileID})
        s.commit()

def update_deadline(id: int, deadline: datetime):
    """ Updates the deadline of the activity with the given id. """
    with session() as s:
        s.query(Activity).filter(Activity.id == id).update({Activity.submission_deadline: deadline})
        s.commit()
