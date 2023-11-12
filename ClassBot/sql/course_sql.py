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

def add_course(teacher_id: int, name: str) -> None:
    """ Adds a new course to the database. """
    with session() as s:
        s.add(Course(teacher_id=teacher_id, name=name))
        s.commit()

def get_courses_by_teacher(teacher_id: int) -> list[Course]:
    """ Returns a list of courses taught by the given teacher. """
    with session() as s:
        return s.query(Course).filter(Course.teacher_id == teacher_id).all()
