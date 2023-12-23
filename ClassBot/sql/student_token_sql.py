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

def add_student_token(student_id: int, token_id: int, value: int, teacher_id: int = None) -> None:
    """ Adds a new student_token to the database. """
    with session() as s:
        s.add(Student_token(student_id=student_id, token_id=token_id, teacher_id=teacher_id, value=value))
        s.commit()

def exists(student_id: int, token_id: int) -> bool:
    """ Returns True if the student_token exists. """
    with session() as s:
        return s.query(Student_token).filter(Student_token.student_id == student_id).filter(Student_token.token_id == token_id).first() is not None
    
def get_tokens_by_student_and_classroom(student_id: int, classroom_id: int) -> list[Token]:
    """ Returns a list of tokens for the given student and classroom. """
    with session() as s:
        return s.query(Token).join(Student_token).filter(Student_token.student_id == student_id).filter(Token.classroom_id == classroom_id).all()

def get_value(student_id: int, token_id: int) -> int:
    """ Returns the value of the student_token. """
    with session() as s:
        return s.query(Student_token).filter(Student_token.student_id == student_id).filter(Student_token.token_id == token_id).first().value
    
def get_total_value_by_classroom(student_id: int, classroom_id: int) -> int:
    """ Returns the total value of the student_token rows where the classroom_id
    of the token with the token_id in student_token is the given classroom_id. """
    with session() as s:
        return sum([student_token.value for student_token in s.query(Student_token).filter(Student_token.student_id == student_id).join(Token).filter(Token.classroom_id == classroom_id).all()])

def get_student_token_by_student_and_classroom(student_id: int, classroom_id: int) -> list[Student_token]:
    """ Returns a list of student_tokens for the given student and classroom. 
    sorted by date of creation from recent to old."""
    with session() as s:
        return s.query(Student_token).filter(Student_token.student_id == student_id).join(Token).filter(Token.classroom_id == classroom_id).order_by(Student_token.creation_date.desc()).all()

def remove_token(student_id: int, token_id: int) -> None:
    """ Removes the token from the student. """
    with session() as s:
        student_token = s.execute(select(Student_token).where(Student_token.student_id == student_id).where(Student_token.token_id == token_id)).scalar_one()
        s.delete(student_token)
        s.commit()
