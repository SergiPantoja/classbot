from sqlalchemy import select
from sqlalchemy.sql import func

from models.pending import Pending
from models.token import Token
from sql import session


def get_pending(id: int) -> Pending | None:
    """ Returns a pending object with the given id. None if not found."""
    with session() as s:
        return s.query(Pending).filter(Pending.id == id).first()

def get_token(pending_id: int) -> Token | None:
    """ If this pending has a non-null token_id, returns the token object with that id. None if not found."""
    with session() as s:
        pending = s.query(Pending).filter(Pending.id == pending_id).first()
        if pending.token_id:
            return s.query(Token).filter(Token.id == pending.token_id).first()
        else:
            return None
        
def get_pendings_of_student_by_type(student_id: int, classroom_id: int, token_type_id: int) -> list[Pending]:
    """ Returns a list of pendings of the given student with the given token_type. """
    with session() as s:
        return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.student_id == student_id, Pending.token_type_id == token_type_id).order_by(Pending.creation_date.desc()).all()

def get_pending_of_student_by_token(student_id: int, classroom_id: int, token_id: int) -> Pending | None:
    """ Returns the pending of the given student with the given token. None if not found. 
        Should only return one pending.
        This is used to check if a student has already sent a pending with the same token.
    """
    with session() as s:
        return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.student_id == student_id, Pending.token_id == token_id).first()

def get_last_pending_of_student_by_type(student_id: int,  classroom_id: int, token_type_id: int) -> Pending | None:
    """ Returns the last pending of the given student with the given token_type. None if not found. """
    with session() as s:
        return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.student_id == student_id, Pending.token_type_id == token_type_id).order_by(Pending.creation_date.desc()).first()

def update_token(pending_id: int, token_id: int) -> None:
    """ Updates the token_id of the pending. """
    with session() as s:
        s.query(Pending).filter(Pending.id == pending_id).update({"token_id": token_id})
        s.commit()

def get_pendings_by_classroom(classroom_id: int, status: str = None, direct_pending: int = None) -> list[Pending]:
    """ Returns a list of pendings belonging to the given classroom. 
    sort by creation_date from newest to oldest. If approved, sort by approved_date from newest to oldest.
    If status is given, only returns pendings with that status. 
    status can be "PENDING", "APPROVED" or "REJECTED".
    direct_pendings is the teacher_id, if given, only returns pendings with that teacher_id. 
    else, returns pendings with teacher_id = None. """
    with session() as s:
        if status:
            if status == "APPROVED":
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.status == status, Pending.teacher_id == direct_pending).order_by(Pending.approved_date.desc()).all()
            else:
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.status == status, Pending.teacher_id == direct_pending).order_by(Pending.creation_date.desc()).all()
        else:
            return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.teacher_id == direct_pending).order_by(Pending.creation_date.desc()).all()
    
def get_pendings_by_student(student_id: int, classroom_id: int, status: str = None, direct_pending: int = None) -> list[Pending]:
    """ Returns a list of pendings belonging to the given student. 
    sort by creation_date from newest to oldest. If approved, sort by approved_date from newest to oldest.
    If status is given, only returns pendings with that status. 
    status can be "PENDING", "APPROVED" or "REJECTED".
    direct_pendings is the teacher_id, if given, only returns pendings with that teacher_id. 
    else, returns pendings with teacher_id = None. """
    with session() as s:
        if status:
            if status == "APPROVED":
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.student_id == student_id, Pending.status == status, Pending.teacher_id == direct_pending).order_by(Pending.approved_date.desc()).all()
            else:
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.student_id == student_id, Pending.status == status, Pending.teacher_id == direct_pending).order_by(Pending.creation_date.desc()).all()
        else:
            return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.student_id == student_id, Pending.teacher_id == direct_pending).order_by(Pending.creation_date.desc()).all()

def get_pendings_by_token_type(token_type_id: int, classroom_id: int, status: str = None, direct_pending: int = None) -> list[Pending]:
    """ Returns a list of pendings belonging to the given token_type. 
    sort by creation_date from newest to oldest. If approved, sort by approved_date from newest to oldest.
    If status is given, only returns pendings with that status. 
    status can be "PENDING", "APPROVED" or "REJECTED".
    direct_pendings is the teacher_id, if given, only returns pendings with that teacher_id. 
    else, returns pendings with teacher_id = None. """
    with session() as s:
        if status:
            if status == "APPROVED":
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.token_type_id == token_type_id, Pending.status == status, Pending.teacher_id == direct_pending).order_by(Pending.approved_date.desc()).all()
            else:
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.token_type_id == token_type_id, Pending.status == status, Pending.teacher_id == direct_pending).order_by(Pending.creation_date.desc()).all()
        else:
            return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.token_type_id == token_type_id, Pending.teacher_id == direct_pending).order_by(Pending.creation_date.desc()).all()

def get_direct_pendings_of_teacher(teacher_id: int, classroom_id: int, status: str = None) -> list[Pending]:
    """ Returns a list of direct pendings belonging to the given teacher. 
    sort by creation_date from newest to oldest. If approved, sort by approved_date from newest to oldest.
    If status is given, only returns pendings with that status. 
    status can be "PENDING", "APPROVED" or "REJECTED" """
    with session() as s:
        if status:
            if status == "APPROVED":
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.teacher_id == teacher_id, Pending.status == status).order_by(Pending.approved_date.desc()).all()
            else:
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.teacher_id == teacher_id, Pending.status == status).order_by(Pending.creation_date.desc()).all()
        else:
            return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.teacher_id == teacher_id).order_by(Pending.creation_date.desc()).all()

def get_approved_pendings_of_teacher(teacher_id: int, classroom_id: int) -> list[Pending]:
    """ Returns a list of approved pendings approved by the given teacher.
    sort by approved_date from newest to oldest. """
    with session() as s:
        return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.approved_by == teacher_id).order_by(Pending.approved_date.desc()).all()

def get_pendings_by_guild(guild_id: int, classroom_id: int, status: str = None, direct_pending: int = None) -> list[Pending]:
    """ Returns a list of pendings belonging to the given guild. 
    sort by creation_date from newest to oldest. If approved, sort by approved_date from newest to oldest.
    If status is given, only returns pendings with that status. 
    status can be "PENDING", "APPROVED" or "REJECTED".
    direct_pendings is the teacher_id, if given, only returns pendings with that teacher_id. 
    else, returns pendings with teacher_id = None. """
    with session() as s:
        if status:
            if status == "APPROVED":
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.guild_id == guild_id, Pending.status == status, Pending.teacher_id == direct_pending).order_by(Pending.approved_date.desc()).all()
            else:
                return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.guild_id == guild_id, Pending.status == status, Pending.teacher_id == direct_pending).order_by(Pending.creation_date.desc()).all()
        else:
            return s.query(Pending).filter(Pending.classroom_id == classroom_id, Pending.guild_id == guild_id, Pending.teacher_id == direct_pending).order_by(Pending.creation_date.desc()).all()


def add_pending(student_id: int, classroom_id: int, token_type_id: int, token_id: int = None, teacher_id: int = None, guild_id: int = None, status: str = "PENDING", approved_by: int = None, text: str = None, FileID: str = None) -> None:
    """ Adds a new pending to the database. """
    with session() as s:
        if status == "APPROVED":
            s.add(Pending(student_id=student_id, classroom_id=classroom_id, token_type_id=token_type_id, token_id=token_id, teacher_id=teacher_id, guild_id=guild_id, status=status, approved_by=approved_by, approved_date=func.now(), text=text, FileID=FileID))
        else:
            s.add(Pending(student_id=student_id, classroom_id=classroom_id, token_type_id=token_type_id, token_id=token_id, teacher_id=teacher_id, guild_id=guild_id, status=status, text=text, FileID=FileID))
        s.commit()

def approve_pending(pending_id: int, approved_by: int) -> None:
    """ Approves the pending. """
    with session() as s:
        s.query(Pending).filter(Pending.id == pending_id).update({"status": "APPROVED", "approved_date": func.now(), "approved_by": approved_by})
        s.commit()

def reject_pending(pending_id: int, explanation: str = None) -> None:
    """ Rejects the pending. """
    with session() as s:
        s.query(Pending).filter(Pending.id == pending_id).update({"status": "REJECTED", "explanation": explanation})    # maybe add a date and teacher?
        s.commit()

def assign_pending(pending_id: int, teacher_id: int) -> None:
    """ Assigns the pending to the given teacher. """
    with session() as s:
        s.query(Pending).filter(Pending.id == pending_id).update({"teacher_id": teacher_id})
        s.commit()

def ask_for_more_info(pending_id: int, info: str) -> None:
    """ Asks for more info to the student. """
    with session() as s:
        # get the current text
        pending = s.query(Pending).filter(Pending.id == pending_id).first()
        current_text = pending.text
        if current_text:
            current_text += "\n\n" + info
        else:
            current_text = info
        s.query(Pending).filter(Pending.id == pending_id).update({"more_info": "PENDING", "text": current_text})
        s.commit()

def send_more_info(pending_id: int, info: str, FileID: str = None) -> None:
    """ Sends more info to the teacher. """
    with session() as s:
        # get the current text
        pending = s.query(Pending).filter(Pending.id == pending_id).first()
        current_text = pending.text
        if current_text:
            current_text += "\n\n" + info
        else:
            current_text = info
        current_file = pending.FileID
        if current_file and FileID == None:
            FileID = current_file   # To avoid deleting the file
        s.query(Pending).filter(Pending.id == pending_id).update({"more_info": "SENT", "text": current_text, "FileID": FileID})
        s.commit()

def delete_pending(pending_id: int) -> None:
    """ Deletes the pending. """
    with session() as s:
        # get pending
        pending = s.execute(select(Pending).where(Pending.id == pending_id)).scalar_one()
        # delete pending
        s.delete(pending)
        s.commit()
