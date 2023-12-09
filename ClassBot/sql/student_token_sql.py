from sqlalchemy import select

from models.student_token import Student_token
from models.token import Token
from sql import session


def get_student_ids(token_id: int) -> list[int]:
    """ Returns a list of student ids for the given token. """
    with session() as s:
        return [student_token.student_id for student_token in s.query(Student_token).filter(Student_token.token_id == token_id).all()]

def get_token_ids(student_id: int) -> list[int]:
    """ Returns a list of token ids for the given student. """
    with session() as s:
        return [student_token.token_id for student_token in s.query(Student_token).filter(Student_token.student_id == student_id).all()]

def add_student_token(student_id: int, token_id: int, teacher_id: int = None) -> None:
    """ Adds a new student_token to the database. """
    with session() as s:
        s.add(Student_token(student_id=student_id, token_id=token_id, teacher_id=teacher_id))
        s.commit()

def exists(student_id: int, token_id: int) -> bool:
    """ Returns True if the student_token exists. """
    with session() as s:
        return s.query(Student_token).filter(Student_token.student_id == student_id).filter(Student_token.token_id == token_id).first() is not None
    
def get_tokens_by_student_and_course(student_id: int, course_id: int) -> list[Token]:
    """ Returns a list of tokens for the given student and course. """
    with session() as s:
        return s.query(Token).join(Student_token).filter(Student_token.student_id == student_id).filter(Token.course_id == course_id).all()


def remove_token(student_id: int, token_id: int) -> None:
    """ Removes the token from the student. """
    with session() as s:
        student_token = s.execute(select(Student_token).where(Student_token.student_id == student_id).where(Student_token.token_id == token_id)).scalar_one()
        s.delete(student_token)
        s.commit()
