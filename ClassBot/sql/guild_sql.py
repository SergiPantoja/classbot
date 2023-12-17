import datetime

from sqlalchemy import select

from models.guild import Guild
from sql import session


def get_guild(id: int) -> Guild | None:
    """ Returns a guild object with the given id. None if not found."""
    with session() as s:
        return s.query(Guild).filter(Guild.id == id).first()

def get_guilds_by_classroom(classroom_id: int) -> list[Guild]:
    """ Returns a list of guilds belonging to the given classroom. 
    order by name"""
    with session() as s:
        return s.query(Guild).filter(Guild.classroom_id == classroom_id).order_by(Guild.name).all()


def add_guild(classroom_id: int, name: str) -> None:
    """ Adds a new guild to the database. """
    with session() as s:
        s.add(Guild(classroom_id=classroom_id, name=name))
        s.commit()

def update_guild_name(id: int, name: str) -> None:
    """ Updates the name of the guild with the given id. """
    with session() as s:
        s.query(Guild).filter(Guild.id == id).update({"name": name})
        s.commit()

def delete_guild(id: int) -> None:
    """ Deletes the guild from the database. """
    with session() as s:
        # get guild
        guild = s.execute(select(Guild).where(Guild.id == id)).scalar_one()
        # delete guild
        s.delete(guild)
        s.commit()
