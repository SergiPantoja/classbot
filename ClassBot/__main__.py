""" Entry point of the application."""
from sqlalchemy.orm import sessionmaker

from utils.logger import logger


logger.info("Starting ClassBot...")


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
