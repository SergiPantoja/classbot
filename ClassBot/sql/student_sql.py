from models.student import Student
from models.classroom import Classroom
from models.student_classroom import Student_classroom
from sql import session


def get_student(id: int) -> Student | None:
    """ Returns a student object with the given id. None if not found."""
    with session() as s:
        return s.query(Student).filter(Student.id == id).first()
    
def get_student_active_classroom(student_id: int) -> Classroom:
    """ Returns the active classroom for the given student. """
    with session() as s:
        student = s.query(Student).filter(Student.id == student_id).first()
        return student.active_classroom

def set_student_active_classroom(student_id: int, classroom_id: int) -> None:
    """ Sets the active classroom for the given student. """
    with session() as s:
        student = s.query(Student).filter(Student.id == student_id).first()
        student.active_classroom_id = classroom_id
        s.commit()

def get_students_by_classroom(classroom_id: int) -> list[Student]:
    """ Returns a list of students for the given classroom. """
    with session() as s:
        return s.query(Student).join(Student_classroom).filter(Student_classroom.classroom_id == classroom_id).all()


def add_student(user_id: int) -> None:
    """ Adds a new student to the database. """
    with session() as s:
        s.add(Student(id=user_id))
        s.commit()

