import datetime

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from utils.logger import logger
from bot.utils import states, keyboards
from bot.utils.inline_keyboard_pagination import paginated_keyboard, paginator_handler
from bot.utils.pagination import Paginator, text_paginator_handler
from bot.utils.clean_context import clean_student_context
from sql import user_sql, student_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, teacher_classroom_sql, token_sql, student_token_sql
from bot.student_inventory import back_to_student_menu


async def student_actions(update: Update, context: ContextTypes):
    """Shows the student actions menu"""
    # Sanitize context.user_data
    clean_student_context(context)

    # check user role
    if "role" not in context.user_data:
        await update.message.reply_text(
            "La sesión ha expirado, por favor inicia sesión nuevamente",
            reply_markup=ReplyKeyboardMarkup(
                [["/start"]], resize_keyboard=True
            )
        )
        return ConversationHandler.END
    elif context.user_data["role"] != "student":
        await update.message.reply_text(
            "No tienes permiso para acceder a este comando",
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Acciones",
        reply_markup=InlineKeyboardMarkup(keyboards.STUDENT_ACTIONS),
    )
    return states.STUDENT_ACTIONS_SELECT_ACTION

async def select_action(update: Update, context: ContextTypes):
    """Selects the student action"""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "action_class_intervention":
        return ConversationHandler.END #todo
    if action == "action_teacher_correction":
        return ConversationHandler.END #todo
    if action == "action_status_phrase":
        return ConversationHandler.END #todo
    if action == "action_diary_update":
        return ConversationHandler.END #todo
    if action == "action_meme":
        return ConversationHandler.END #todo
    if action == "action_joke":
        return ConversationHandler.END #todo
    if action == "action_misc":
        await query.edit_message_text(
            "Envíe un mensaje con la miscelánea que desea proponer",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.STUDENT_ACTIONS_SEND_MISC
    
async def send_misc(update: Update, context: ContextTypes):
    "Creates a new miscelanious pending"

    # get necessary data
    user = user_sql.get_user_by_chatid(update.effective_user.id)
    student = student_sql.get_student(user.id)
    classroom_id = student.active_classroom_id
    token_type_id = token_type_sql.get_token_type_by_type("Miscelaneo").id

    # get file id if exists
    file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id
    
    text = f"{user.fullname} ha propuesto una miscelánea:\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"

    # create pending in database
    pending_sql.add_pending(student.id, classroom_id, token_type_id, text=text, FileID=fid)
    logger.info(f"New misc by {user.fullname}.")
    #TODO send notification to notification channel of the classroom if it exists
    
    # notify student that the proposal was sent
    await update.message.reply_text(
        "Propuesta enviada.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )
    return ConversationHandler.END

async def student_actions_back(update: Update, context: ContextTypes):
    """Goes back to the student menu"""
    query = update.callback_query
    query.answer()

    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(student.active_classroom_id)
    course_name = course_sql.get_course(classroom.course_id).name

    await query.message.reply_text(
        f"Menú principal"
        f"Curso: {course_name}\n"
        f"Aula: {classroom.name}\n",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )

    if "actions" in context.user_data:
        context.user_data.pop("actions")
    return ConversationHandler.END


# Handlers   
student_actions_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Acciones$"), student_actions)],
    states={
        states.STUDENT_ACTIONS_SELECT_ACTION: [CallbackQueryHandler(select_action, pattern=r"^action_")],
        states.STUDENT_ACTIONS_SEND_MISC: [MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.Sticker.ALL) & ~filters.COMMAND, send_misc)],
    },
    fallbacks=[
        CallbackQueryHandler(student_actions_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_student_menu)
    ],
    allow_reentry=True,
)
