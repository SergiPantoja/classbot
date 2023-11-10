from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from utils.logger import logger
from models.base import Base


def start() -> Session:
    # set up database
    engine = create_engine("sqlite:///classbot.db", echo=True)
    logger.info("Created database engine.")

    Base.metadata.create_all(engine)
    logger.info("Created database tables.")

    # Create a session factory
    Session = sessionmaker(bind=engine)

    # Create a new session
    session = Session()

    return session

try:
    session = start()
except Exception as e:
    logger.exception(f"failed to connect due to {e}")
    raise e

logger.info("Connected to database.")
