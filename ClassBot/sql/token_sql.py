from sqlalchemy import select

from models.token import Token
from sql import session


def get_token(id: int) -> Token | None:
    """ Returns a token object with the given id. None if not found."""
    with session() as s:
        return s.query(Token).filter(Token.id == id).first()

def get_token_by_name(name: str) -> Token | None:
    """ Returns the first token object with the given name. None if not found."""
    with session() as s:
        return s.query(Token).filter(Token.name == name).first()

def get_token_by_pending(pending_id: int) -> Token | None:
    """ Returns the first token object with the given pending_id. None if not found."""
    with session() as s:
        return s.query(Token).filter(Token.pending_id == pending_id).first()


def add_token(
        name: str, 
        value: int,
        token_type_id: int, 
        course_id: int, 
        teacher_creator_id: int = None,
        pending_id: int = None,
        description: str = None,
        image_url: str = None,
        ):
    """ Adds a new token to the database. """
    with session() as s:
        s.add(Token(
            name=name, 
            value=value,
            token_type_id=token_type_id, 
            course_id=course_id, 
            teacher_creator_id=teacher_creator_id,
            pending_id=pending_id,
            description=description,
            image_url=image_url,
        ))
        s.commit()
