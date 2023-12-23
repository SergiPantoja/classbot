import datetime

from sqlalchemy import select

from models.practic_class_exercise import Practic_class_exercise
from sql import session
import sql.activity_sql as activity_sql
import sql.token_sql as token_sql
import sql.practic_class_sql as practic_class_sql


def get_practic_class_exercise(id: int) -> Practic_class_exercise | None:
    """ Returns a practic_class_exercise object with the given id. None if not found."""
    with session() as s:
        return s.query(Practic_class_exercise).filter(Practic_class_exercise.id == id).first()

def get_practic_class_exercise_by_activity_id(activity_id: int) -> Practic_class_exercise | None:
    """ Returns a practic_class_exercise object with the given activity_id. None if not found."""
    with session() as s:
        return s.query(Practic_class_exercise).filter(Practic_class_exercise.activity_id == activity_id).first()

def get_practic_class_exercises_by_practic_class_id(practic_class_id: int) -> list[Practic_class_exercise]:
    """ Returns a list of practic_class_exercise objects with the given practic_class_id."""
    with session() as s:
        return s.query(Practic_class_exercise).filter(Practic_class_exercise.practic_class_id == practic_class_id).all()

def add_practic_class_exercise(
        value: int,
        practic_class_id: int,
        activity_id: int,
        classroom_id: int,
        name: str,
        partial_credits_allowed: bool = False,
        description: str = None,
        FileID: str = None,
        deadline: datetime = None,
    ):
    """ Adds a new practic_class_exercise to the database. """
    with session() as s:
        activity_type_id = practic_class_sql.get_practic_class(practic_class_id).activity_type_id
        activity_sql.add_activity(
            activity_type_id,
            classroom_id,
            name,
            description,
            FileID,
            deadline,
        )
        activity_id = activity_sql.get_activity_by_token_id(token_sql.get_last_token().id).id
        s.add(Practic_class_exercise(
            value=value,
            practic_class_id=practic_class_id,
            activity_id=activity_id,
            partial_credits_allowed=partial_credits_allowed,
        ))
        s.commit()

def update_value(id: int, value: int):  
    """ Updates the value of the practic_class_exercise with the given id. """
    with session() as s:
        s.query(Practic_class_exercise).filter(Practic_class_exercise.id == id).update({"value": value})
        s.commit()

def update_partial_credits_allowed(id: int, partial_credits_allowed: bool):
    """ Updates the partial_credits_allowed of the practic_class_exercise with the given id. """
    with session() as s:
        s.query(Practic_class_exercise).filter(Practic_class_exercise.id == id).update({"partial_credits_allowed": partial_credits_allowed})
        s.commit()

def update_name(id: int, name: str):
    """ Updates the name of the activity associated with this practic_class_exercise. """
    with session() as s:
        activity = s.query(Practic_class_exercise).filter(Practic_class_exercise.id == id).first()
        activity_sql.update_name(activity.activity_id, name)
        s.commit()

def update_description(id: int, description: str):
    """ Updates the description of the activity associated with this practic_class_exercise. """
    with session() as s:
        activity = s.query(Practic_class_exercise).filter(Practic_class_exercise.id == id).first()
        activity_sql.update_description(activity.activity_id, description)
        s.commit()

def update_file(id: int, FileID: str):
    """ Updates the FileID of the activity associated with this practic_class_exercise. """
    with session() as s:
        activity = s.query(Practic_class_exercise).filter(Practic_class_exercise.id == id).first()
        activity_sql.update_file(activity.activity_id, FileID)
        s.commit()
