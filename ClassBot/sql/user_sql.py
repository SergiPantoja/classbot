from models.user import User
from sql import session


def get_user(id: int) -> User | None:
    """ Returns a user object with the given id. None if not found."""
    with session() as s:
        return s.query(User).filter(User.id == id).first()

def get_user_by_chatid(chatid: int) -> User | None:
    """ Returns a user object with the given chatid. None if not found."""
    with session() as s:
        return s.query(User).filter(User.telegram_chatid == chatid).first()

def add_user(chatid: int, fullname: str) -> None:
    """ Adds a new user to the database. """
    with session() as s:
        s.add(User(telegram_chatid=chatid, fullname=fullname))
        s.commit()
