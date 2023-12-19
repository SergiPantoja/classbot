from sqlalchemy import select

from models.guild_token import Guild_token
from models.token import Token
from sql import session


def get_guild_ids(token_id: int) -> list[int]:
    """ Returns a list of guild ids for the given token. """
    with session() as s:
        return [guild_token.guild_id for guild_token in s.query(Guild_token).filter(Guild_token.token_id == token_id).all()]

def get_token_ids(guild_id: int) -> list[int]:
    """ Returns a list of token ids for the given guild. """
    with session() as s:
        return [guild_token.token_id for guild_token in s.query(Guild_token).filter(Guild_token.guild_id == guild_id).all()]

def add_guild_token(guild_id: int, token_id: int, value: int) -> None:
    """ Adds a new guild_token to the database. """
    with session() as s:
        s.add(Guild_token(guild_id=guild_id, token_id=token_id, value=value))
        s.commit()

def exists(guild_id: int, token_id: int) -> bool:
    """ Returns True if the guild_token exists. """
    with session() as s:
        return s.query(Guild_token).filter(Guild_token.guild_id == guild_id).filter(Guild_token.token_id == token_id).first() is not None
    
def get_tokens_by_guild_and_classroom(guild_id: int, classroom_id: int) -> list[Token]:
    """ Returns a list of tokens for the given guild and course. """
    with session() as s:
        return s.query(Token).join(Guild_token).filter(Guild_token.guild_id == guild_id).filter(Token.classroom_id == classroom_id).all()


def remove_token(guild_id: int, token_id: int) -> None:
    """ Removes the token from the guild. """
    with session() as s:
        guild_token = s.execute(select(Guild_token).where(Guild_token.guild_id == guild_id).where(Guild_token.token_id == token_id)).scalar_one()
        s.delete(guild_token)
        s.commit()
