from models.teacher import Teacher
from models.classroom import Classroom
from sql import session


def get_teacher(id: int) -> Teacher | None:
    """ Returns a teacher object with the given id. None if not found."""
    with session() as s:
        return s.query(Teacher).filter(Teacher.id == id).first()

def add_teacher(user_id: int) -> None:
    """ Adds a new teacher to the database. """
    with session() as s:
        s.add(Teacher(id=user_id))
        s.commit()

def get_teacher_courses(teacher_id: int) -> list:
    """ Returns a list of courses for the given teacher. """
    with session() as s:
        teacher = s.query(Teacher).filter(Teacher.id == teacher_id).first()
        return teacher.courses
    
def get_teacher_active_classroom(teacher_id: int) -> Classroom:
    """ Returns the active classroom for the given teacher. """
    with session() as s:
        teacher = s.query(Teacher).filter(Teacher.id == teacher_id).first()
        return teacher.active_classroom

def set_teacher_active_classroom(teacher_id: int, classroom_id: int) -> None:
    """ Sets the active classroom for the given teacher. """
    with session() as s:
        teacher = s.query(Teacher).filter(Teacher.id == teacher_id).first()
        teacher.active_classroom_id = classroom_id
        s.commit()
