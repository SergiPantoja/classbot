""" This module contains mostly command/message handlers for the bot that 
usually need to desambiguate using context data. For example, between a teacher
and a student or depending on what menu the user is navigating."""
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, ConversationHandler

from bot.teacher_settings import teacher_settings, back_to_teacher_menu
from bot.student_inventory import back_to_student_menu


async def handle_keyerror(update: Update, context: ContextTypes):   
    """ if a keyerror in context appears, most likely because bot restarted, 
    users will need to log in again."""
    await update.message.reply_text(
        "La sesión ha expirado, por favor inicia sesión nuevamente",
        reply_markup=ReplyKeyboardMarkup(
            [["/start"]], resize_keyboard=True
        )
    )

async def settings(update: Update, context: ContextTypes):
    """ Process the "Opciones" update, it checks if the user is a teacher or a 
    student and sends the update to the correct handler. """

    try:
        role = context.user_data["role"]
    except:
        await handle_keyerror(update, context)
        raise KeyError("Keyerror in settings: User role not found in context.user_data")
    
    if role == "teacher":
        await teacher_settings(update, context)
    else:
        pass
        #await student_settings(update, context)

async def back_to_menu(update: Update, context: ContextTypes):
    """Returns to the main menu"""
    try:
        role = context.user_data["role"]
    except:
        await handle_keyerror(update, context)
        raise KeyError("Keyerror in settings: User role not found in context.user_data")
    
    if role == "teacher":
        await back_to_teacher_menu(update, context)
    else:
        await back_to_student_menu(update, context)

async def log_out(update: Update, context: ContextTypes):
    """Logs out the user
    Accessible from the settings menu"""
    # Clears user context
    context.user_data.clear()

    await update.message.reply_text(
        "Sesión cerrada",
        reply_markup=ReplyKeyboardMarkup(
            [["/start"]], resize_keyboard=True
        )
    )
    return ConversationHandler.END


# Handlers
settings_handler = MessageHandler(filters.Regex("^Opciones$"), settings)
back_to_menu_handler = MessageHandler(filters.Regex("^Atrás$"), back_to_menu)
log_out_handler = MessageHandler(filters.Regex("^Salir$"), log_out)
