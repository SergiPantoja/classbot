from models.classroom import Classroom
from sql import session

def get_classroom(id: int) -> Classroom | None:
    """ Returns a classroom object with the given id. None if not found."""
    with session() as s:
        return s.query(Classroom).filter(Classroom.id == id).first()

def get_classroom_by_name(name: str) -> Classroom | None:
    """ Returns the first classroom object with the given name. None if not found."""
    with session() as s:
        return s.query(Classroom).filter(Classroom.name == name).first()
    
def get_classroom_by_teacher_auth(teacher_auth: str) -> Classroom | None:   # since it's unique, it should return only one
    """ Returns the first classroom object with the given teacher_auth. None if not found."""
    with session() as s:
        return s.query(Classroom).filter(Classroom.teacher_auth == teacher_auth).first()
    
def get_classroom_by_student_auth(student_auth: str) -> Classroom | None:   # since it's unique, it should return only one
    """ Returns the first classroom object with the given student_auth. None if not found."""
    with session() as s:
        return s.query(Classroom).filter(Classroom.student_auth == student_auth).first()

def get_classrooms_by_course(course_id: int) -> list[Classroom]:
    """ Returns a list of classrooms belonging to the given course. """
    with session() as s:
        return s.query(Classroom).filter(Classroom.course_id == course_id).all()

def add_classroom(course_id: int, name: str, teacher_auth: str, student_auth: str) -> None:
    """ Adds a new classroom to the database. """
    with session() as s:
        s.add(Classroom(course_id=course_id, name=name, teacher_auth=teacher_auth, student_auth=student_auth))
        s.commit()
