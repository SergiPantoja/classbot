from sqlalchemy import select

from models.token_type import Token_type
from sql import session


def get_token_type(id: int) -> Token_type | None:
    """ Returns a token_type object with the given id. None if not found."""
    with session() as s:
        return s.query(Token_type).filter(Token_type.id == id).first()
    
def get_token_type_by_type(type: str, classroom_id: int = None) -> Token_type | None:
    """ Returns the first token_type object with the given type. None if not found.
        In this case type is unique as long as is a default type, meaning classroom_id is None.
        Is not related to a classroom. If it is related to a course, then type is not unique, 
        but the combination of type and classroom_id is unique."""
    with session() as s:
        return s.query(Token_type).filter(Token_type.type == type, Token_type.classroom_id == classroom_id).first()

def get_token_types(classroom_id: int = None, include_hidden: bool = False) -> list[Token_type]:
    """ Return a list of token_type objects with the given classroom_id. If include_hidden is True, then also include hidden token_types."""
    with session() as s:
        if include_hidden:
            return s.query(Token_type).filter(Token_type.classroom_id == classroom_id).all()
        else:
            return s.query(Token_type).filter(Token_type.classroom_id == classroom_id, Token_type.hidden == False).all()

def switch_hidden_status(id: int) -> None:
    """ Switches the hidden status of the token_type with the given id. """
    token_type = get_token_type(id)
    if token_type is None:
        return
    with session() as s:
        token_type.hidden = not token_type.hidden
        s.commit()

def add_token_type(type: str, classroom_id: int = None, hidden: bool = False) -> None:
    """ Adds a new token_type to the database. """
    with session() as s:
        s.add(Token_type(type=type, classroom_id=classroom_id, hidden=hidden))
        s.commit()
