from sqlalchemy import select

from models.activity_type import Activity_type
from sql import session
import sql.token_type_sql as token_type_sql


def get_activity_type(id: int) -> Activity_type | None:
    """ Returns an activity_type object with the given id. None if not found."""
    with session() as s:
        return s.query(Activity_type).filter(Activity_type.id == id).first()

def get_activity_type_by_type(type: str, classroom_id: int) -> Activity_type | None:
    """ Returns the first activity_type object with the token_type_id of the token
        with the given type and classroom_id. None if not found.
        Since the token_type_id is unique, this function will return only one object.
        And since the combination of type and classroom_id is unique, there will be only one token_type.
        If the token_type is not found, then the activity_type is not found either."""
    token_type = token_type_sql.get_token_type_by_type(type, classroom_id)
    if token_type is None:
        return None
    with session() as s:
        return s.query(Activity_type).filter(Activity_type.token_type_id == token_type.id).first()

def get_activity_type_by_token_type_id(token_type_id: int) -> Activity_type | None:
    """ Returns the first activity_type object with the given token_type_id. None if not found.
        Since the token_type_id is unique, this function will return only one object."""
    with session() as s:
        return s.query(Activity_type).filter(Activity_type.token_type_id == token_type_id).first()

def get_activity_types(classroom_id: int, include_hidden: bool = False) -> list[Activity_type]:
    """ Return a list of activity_type objects with the token_type_id of the token_types
        with the given classroom_id. If include_hidden is True, then also include hidden activity_types."""
    token_types = token_type_sql.get_token_types(classroom_id, include_hidden)
    with session() as s:
        return s.query(Activity_type).filter(Activity_type.token_type_id.in_([token_type.id for token_type in token_types])).all()

def add_activity_type(
        type: str, 
        classroom_id: int, 
        hidden: bool = False, 
        description: str = None,
        guild_activity: bool = False,
        single_submission: bool = False,
        FileID: str = None,
    ):
    """ Adds a new activity_type to the database. 
    Creates a new token_type and adds it to the database, then assigns it to the activity_type."""
    with session() as s:
        token_type_sql.add_token_type(type, classroom_id, hidden)
        token_type = token_type_sql.get_token_type_by_type(type, classroom_id)
        s.add(Activity_type(
            token_type_id=token_type.id,
            description=description,
            guild_activity=guild_activity,
            single_submission=single_submission,
            FileID=FileID,
        ))
        s.commit()

def update_description(id: int, description: str):
    """ Updates the description of the activity_type with the given id."""
    with session() as s:
        activity_type = s.query(Activity_type).filter(Activity_type.id == id).first()
        activity_type.description = description
        s.commit()

def update_file(id: int, FileID: str):
    """ Updates the FileID of the activity_type with the given id."""
    with session() as s:
        activity_type = s.query(Activity_type).filter(Activity_type.id == id).first()
        activity_type.FileID = FileID
        s.commit()

def hide_activity_type(id: int):
    """ Hides the token_type associated with the activity_type with the given id."""
    with session() as s:
        activity_type = s.query(Activity_type).filter(Activity_type.id == id).first()
        token_type_sql.hide_token_type(activity_type.token_type_id)
        s.commit()

def unhide_activity_type(id: int):
    """ Unhides the token_type associated with the activity_type with the given id."""
    with session() as s:
        activity_type = s.query(Activity_type).filter(Activity_type.id == id).first()
        token_type_sql.unhide_token_type(activity_type.token_type_id)
        s.commit()
