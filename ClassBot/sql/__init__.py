from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from utils.logger import logger
from models.base import Base
from models.token_type import Token_type


def _start():
    # set up database
    engine = create_engine("sqlite:///classbot.db", echo=True)
    logger.info("Created database engine.")

    Base.metadata.create_all(engine)
    logger.info("Created database tables.")

    # Create a session factory
    Session = sessionmaker(bind=engine)

    return Session

def create_default_token_types(session):
    # at the start of the bot, create the default token types usable by the bot
    # in every course.
    with session() as s:
        # create default token types if they don't exist
        if not s.query(Token_type).filter(Token_type.type == "Medalla").first():
            s.add(Token_type(type="Medalla", hidden=True))
        if not s.query(Token_type).filter(Token_type.type == "Miscelaneo").first():
            s.add(Token_type(type="Miscelaneo", hidden=True))
        if not s.query(Token_type).filter(Token_type.type == "Propuesta de título").first():
            s.add(Token_type(type="Propuesta de título", hidden=True)) 
        s.commit()
        


try:
    session = _start()
    create_default_token_types(session)
except Exception as e:
    logger.exception(f"failed to connect due to {e}")
    raise e

logger.info("Connected to database.")
