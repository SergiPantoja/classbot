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


# ptb imports
from telegram.ext import (
    Application,
)



# bot
TOKEN = "5827425180:AAE6HGte6-L50z8IWysZ1jVng02zc1qxDaw"

app = Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).build()



# start the bot (ctrl-c to stop)
app.run_polling()
