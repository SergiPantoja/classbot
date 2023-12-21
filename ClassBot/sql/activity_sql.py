from sqlalchemy import select

from models.activity import Activity
from models.token import Token
from sql import session
import sql.token_sql as token_sql


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
