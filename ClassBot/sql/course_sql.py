from sqlalchemy import select

from models.course import Course
from sql import session

def get_course(id: int) -> Course | None:
    """ Returns a course object with the given id. None if not found."""
    with session() as s:
        return s.query(Course).filter(Course.id == id).first()
    
def get_course_by_name(name: str) -> Course | None:
    """ Returns the first course object with the given name. None if not found."""
    with session() as s:
        return s.query(Course).filter(Course.name == name).first()

def get_courses_by_teacher(teacher_id: int) -> list[Course]:
    """ Returns a list of courses taught by the given teacher. """
    with session() as s:
        return s.query(Course).filter(Course.teacher_id == teacher_id).all()

def add_course(teacher_id: int, name: str) -> None:
    """ Adds a new course to the database. """
    with session() as s:
        s.add(Course(teacher_id=teacher_id, name=name))
        s.commit()

def update_course_name(course_id: int, new_name: str) -> None:
    """ Updates the course name. """
    with session() as s:
        s.query(Course).filter(Course.id == course_id).update({"name": new_name})
        s.commit()

def transfer_course(course_id: int, new_teacher_id: int) -> None:
    """ Transfers the course to a new teacher. """
    with session() as s:
        course = s.execute(select(Course).where(Course.id == course_id)).scalar_one()
        course.teacher_id = new_teacher_id
        s.commit()

def delete_course(course_id: int) -> None:
    """ Deletes the course from the database. """
    with session() as s:
        # get course
        course = s.execute(select(Course).where(Course.id == course_id)).scalar_one()
        # delete course
        s.delete(course)
        s.commit()