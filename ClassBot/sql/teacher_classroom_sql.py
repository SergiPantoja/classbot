from sqlalchemy import select

from models.teacher_classroom import Teacher_classroom
from sql import session


def get_teacher_ids(classroom_id: int) -> list[int]:
    """ Returns a list of teacher ids for the given classroom. """
    with session() as s:
        return [teacher_classroom.teacher_id for teacher_classroom in s.query(Teacher_classroom).filter(Teacher_classroom.classroom_id == classroom_id).all()]

def get_classroom_ids(teacher_id: int) -> list[int]:
    """ Returns a list of classroom ids for the given teacher. """
    with session() as s:
        return [teacher_classroom.classroom_id for teacher_classroom in s.query(Teacher_classroom).filter(Teacher_classroom.teacher_id == teacher_id).all()]

def exists(teacher_id: int, classroom_id: int) -> bool:
    """ Returns True if the teacher_classroom exists. """
    with session() as s:
        return s.query(Teacher_classroom).filter(Teacher_classroom.teacher_id == teacher_id).filter(Teacher_classroom.classroom_id == classroom_id).first() is not None


def add_teacher_classroom(teacher_id: int, classroom_id: int) -> None:
    """ Adds a new teacher_classroom to the database. """
    with session() as s:
        s.add(Teacher_classroom(teacher_id=teacher_id, classroom_id=classroom_id))
        s.commit()

def remove_teacher(teacher_id: int, classroom_id: int) -> None:
    """ Removes the teacher from the classroom. """
    with session() as s:
        teacher_classroom = s.execute(select(Teacher_classroom).where(Teacher_classroom.teacher_id == teacher_id).where(Teacher_classroom.classroom_id == classroom_id)).scalar_one()
        s.delete(teacher_classroom)
        s.commit()
