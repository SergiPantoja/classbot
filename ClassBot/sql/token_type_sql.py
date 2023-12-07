from sqlalchemy import select

from models.token_type import Token_type
from sql import session


def get_token_type(id: int) -> Token_type | None:
    """ Returns a token_type object with the given id. None if not found."""
    with session() as s:
        return s.query(Token_type).filter(Token_type.id == id).first()
    
def get_token_type_by_type(type: str) -> Token_type | None:
    """ Returns the first token_type object with the given type. None if not found.
        In this case type is unique as long as is a default type, meaning course_id is None.
        Is not related to a course. If it is related to a course, then type is not unique, 
        but the combination of type and course_id is unique."""
    with session() as s:
        return s.query(Token_type).filter(Token_type.type == type).first()


def add_token_type(type: str, course_id: int = None, hidden: bool = False) -> None:
    """ Adds a new token_type to the database. """
    with session() as s:
        s.add(Token_type(type=type, course_id=course_id, hidden=hidden))
        s.commit()
