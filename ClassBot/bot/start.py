from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application

from utils.logger import logger
from bot.user_login import user_login_conv

TOKEN = "5827425180:AAE6HGte6-L50z8IWysZ1jVng02zc1qxDaw"    #TEMPORARY TOKEN

def start_bot():
    """Starts the bot"""
    logger.info("Starting ClassBot...")
    app = Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).build()
    _add_handlers(app)
    app.run_polling()


def _add_handlers(app):
    app.add_handler(user_login_conv)
