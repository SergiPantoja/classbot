from sqlalchemy import select

from models.student_token import Student_token
from sql import session


def get_student_ids(token_id: int) -> list[int]:
    """ Returns a list of student ids for the given token. """
    with session() as s:
        return [student_token.student_id for student_token in s.query(Student_token).filter(Student_token.token_id == token_id).all()]

def get_token_ids(student_id: int) -> list[int]:
    """ Returns a list of token ids for the given student. """
    with session() as s:
        return [student_token.token_id for student_token in s.query(Student_token).filter(Student_token.student_id == student_id).all()]

def add_student_token(student_id: int, token_id: int) -> None:
    """ Adds a new student_token to the database. """
    with session() as s:
        s.add(Student_token(student_id=student_id, token_id=token_id))
        s.commit()

def exists(student_id: int, token_id: int) -> bool:
    """ Returns True if the student_token exists. """
    with session() as s:
        return s.query(Student_token).filter(Student_token.student_id == student_id).filter(Student_token.token_id == token_id).first() is not None
    

def remove_token(student_id: int, token_id: int) -> None:
    """ Removes the token from the student. """
    with session() as s:
        student_token = s.execute(select(Student_token).where(Student_token.student_id == student_id).where(Student_token.token_id == token_id)).scalar_one()
        s.delete(student_token)
        s.commit()
