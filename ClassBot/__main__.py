""" Entry point of the application."""
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base


# set up logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
logger.info("Starting ClassBot...")

# set up database
engine = create_engine("sqlite:///classbot.db", echo=True)
logger.info("Created database engine.")

Base.metadata.create_all(engine)
logger.info("Created database tables.")

# Create a session factory
Session = sessionmaker(bind=engine)

def get_session():
    # Create a new session
    session = Session()

    try:
        yield session
    finally:
        session.close()


# ptb imports
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


# db_ops imports
from sql import user_sql

# bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user with this chatid exists
    user = user_sql.get_user_by_chatid(update.effective_chat.id)
    pass
    



# bot
TOKEN = "5827425180:AAE6HGte6-L50z8IWysZ1jVng02zc1qxDaw"

app = Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).build()


# start the bot (ctrl-c to stop)
app.run_polling()
