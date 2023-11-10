""" Entry point of the application."""

import logging


# set up logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
logger.info("Starting ClassBot...")


from sqlalchemy import create_engine

engine = create_engine("sqlite:///classbot.db", echo=True)
logger.info("Created database engine.")

from models.base import Base

Base.metadata.create_all(engine)
logger.info("Created database tables.")
