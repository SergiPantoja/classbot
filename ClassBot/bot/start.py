import traceback
import html
import json

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from utils.logger import logger
from bot.utils.commands import get_chat_id_handler
from bot.context_handlers import settings_handler, back_to_menu_handler, log_out_handler
from bot.user_login import user_login_conv
from bot.teacher_settings import edit_course_conv, edit_classroom_conv
from bot.teacher_conferences import teacher_conferences_conv
from bot.teacher_pendings import teacher_pendings_conv
from bot.student_inventory import student_inventory_handler, inv_medal_conv
from bot.student_conferences import student_conferences_conv
from bot.student_notifications import student_answer_pending_conv


# configs (move to file later)
TOKEN = "5827425180:AAE6HGte6-L50z8IWysZ1jVng02zc1qxDaw"    #TEMPORARY TOKEN
DEV_CHAT = "-1002102603758"

async def error_handler(update: Update, context: ContextTypes):
    """Log Errors caused by Updates."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    error = tb_list[-1]
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    await context.bot.send_message(
        chat_id=DEV_CHAT, text=message, parse_mode=ParseMode.HTML
    )

    msg = "Ups, something went wrong. Please try again or contact the developer if the problem persists.\n" + error 

    # Finally, send the message
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=msg, parse_mode=ParseMode.HTML
    )

def start_bot():
    """Starts the bot"""
    logger.info("Starting ClassBot...")
    app = Application.builder().token(TOKEN).read_timeout(30).write_timeout(30).build()
    _add_handlers(app)
    app.run_polling()


def _add_handlers(app):
    # utils
    app.add_handler(get_chat_id_handler)

    app.add_handler(user_login_conv) 

    app.add_handler(edit_course_conv)   # needs to be first to avoid conflict with other handlers
    app.add_handler(edit_classroom_conv)
    app.add_handler(teacher_conferences_conv)
    app.add_handler(teacher_pendings_conv)

    app.add_handler(inv_medal_conv)
    app.add_handler(student_conferences_conv)
    app.add_handler(student_answer_pending_conv)
    app.add_handler(student_inventory_handler)

    app.add_handler(settings_handler)
    app.add_handler(back_to_menu_handler)
    app.add_handler(log_out_handler)

    app.add_error_handler(error_handler)
