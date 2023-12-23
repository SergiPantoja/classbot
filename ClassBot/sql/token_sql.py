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

def get_last_token() -> Token | None:
    """ Returns the last token in the database. None if not found."""
    with session() as s:
        return s.query(Token).order_by(Token.id.desc()).first()

def add_token(
        name: str, 
        token_type_id: int, 
        classroom_id: int, 
        teacher_creator_id: int = None,
        description: str = None,
        image_url: str = None,
        ):
    """ Adds a new token to the database. """
    with session() as s:
        s.add(Token(
            name=name, 
            token_type_id=token_type_id, 
            classroom_id=classroom_id, 
            teacher_creator_id=teacher_creator_id,
            description=description,
            image_url=image_url,
        ))
        s.commit()

def update_name(id: int, name: str):
    """ Updates the name of the token with the given id. """
    with session() as s:
        s.query(Token).filter(Token.id == id).update({Token.name: name})
        s.commit()

def update_description(id: int, description: str):
    """ Updates the description of the token with the given id. """
    with session() as s:
        s.query(Token).filter(Token.id == id).update({Token.description: description})
        s.commit()

def delete_token(id: int):
    """ Deletes a token from the database. """
    with session() as s:
        # get token
        token = s.execute(select(Token).where(Token.id == id)).scalar_one()
        # delete token
        s.delete(token)
        s.commit()
