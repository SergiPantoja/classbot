from sqlalchemy import select

from models.student_guild import Student_guild
from sql import session


def get_student_ids(guild_id: int) -> list[int]:
    """ Returns a list of student ids for the given guild. """
    with session() as s:
        return [student_guild.student_id for student_guild in s.query(Student_guild).filter(Student_guild.guild_id == guild_id).all()]

def get_guild_ids(student_id: int) -> list[int]:
    """ Returns a list of guild ids for the given student. """
    with session() as s:
        return [student_guild.guild_id for student_guild in s.query(Student_guild).filter(Student_guild.student_id == student_id).all()]

def add_student_guild(student_id: int, guild_id: int) -> None:
    """ Adds a new student_guild to the database. """
    with session() as s:
        s.add(Student_guild(student_id=student_id, guild_id=guild_id))
        s.commit()

def exists(student_id: int, guild_id: int) -> bool:
    """ Returns True if the student_guild exists. """
    with session() as s:
        return s.query(Student_guild).filter(Student_guild.student_id == student_id).filter(Student_guild.guild_id == guild_id).first() is not None


def remove_student(student_id: int, guild_id: int) -> None:
    """ Removes the student from the guild. """
    with session() as s:
        student_guild = s.execute(select(Student_guild).where(Student_guild.student_id == student_id).where(Student_guild.guild_id == guild_id)).scalar_one()
        s.delete(student_guild)
        s.commit()
