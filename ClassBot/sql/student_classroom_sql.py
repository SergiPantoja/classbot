from sqlalchemy import select

from models.student_classroom import Student_classroom
from sql import session

def get_student_ids(classroom_id: int) -> list[int]:
    """ Returns a list of student ids for the given classroom. """
    with session() as s:
        return [student_classroom.student_id for student_classroom in s.query(Student_classroom).filter(Student_classroom.classroom_id == classroom_id).all()]

def get_classroom_ids(student_id: int) -> list[int]:
    """ Returns a list of classroom ids for the given student. """
    with session() as s:
        return [student_classroom.classroom_id for student_classroom in s.query(Student_classroom).filter(Student_classroom.student_id == student_id).all()]

def add_student_classroom(student_id: int, classroom_id: int) -> None:
    """ Adds a new student_classroom to the database. """
    with session() as s:
        s.add(Student_classroom(student_id=student_id, classroom_id=classroom_id))
        s.commit()

def exists(student_id: int, classroom_id: int) -> bool:
    """ Returns True if the student_classroom exists. """
    with session() as s:
        return s.query(Student_classroom).filter(Student_classroom.student_id == student_id).filter(Student_classroom.classroom_id == classroom_id).first() is not None

def remove_student(student_id: int, classroom_id: int) -> None:
    """ Removes the student from the classroom. """
    with session() as s:
        student_classroom = s.execute(select(Student_classroom).where(Student_classroom.student_id == student_id).where(Student_classroom.classroom_id == classroom_id)).scalar_one()
        s.delete(student_classroom)
        s.commit()
