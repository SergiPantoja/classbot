from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters

from utils.logger import logger


async def get_chat_id(update: Update, context: ContextTypes):
    """ Returns the chat id of the current chat. """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Chat id:{update.effective_chat.id}"
    )
    logger.info(f"Chat id:{update.effective_chat.id}")

get_chat_id_handler = MessageHandler(filters.Regex("^/chat_id$"), get_chat_id)
