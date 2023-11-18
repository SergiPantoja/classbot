from telegram.ext import Application

from utils.logger import logger
from bot.context_handlers import settings_handler, back_to_menu_handler, log_out_handler
from bot.user_login import user_login_conv
from bot.teacher_settings import edit_course_conv

TOKEN = "5827425180:AAE6HGte6-L50z8IWysZ1jVng02zc1qxDaw"    #TEMPORARY TOKEN

def start_bot():
    """Starts the bot"""
    logger.info("Starting ClassBot...")
    app = Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).build()
    _add_handlers(app)
    app.run_polling()


def _add_handlers(app):
    app.add_handler(user_login_conv) 

    app.add_handler(edit_course_conv)   # needs to be first to avoid conflict with other handlers
    app.add_handler(settings_handler)
    app.add_handler(back_to_menu_handler)
    app.add_handler(log_out_handler)