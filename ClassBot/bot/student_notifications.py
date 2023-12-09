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
from sql import user_sql, student_sql, classroom_sql, course_sql, pending_sql, token_type_sql, teacher_classroom_sql, token_sql, student_token_sql
from bot.student_inventory import back_to_student_menu


async def student_answer_pending(update: Update, context: ContextTypes):
    """ Sends a message to the student with the pending info and asks for an answer. """
    # Check user role
    if "role" not in context.user_data:
        await update.message.reply_text(
            "La sesión ha expirado, por favor inicia sesión nuevamente",
            reply_markup=ReplyKeyboardMarkup(
                [["/start"]], resize_keyboard=True
            )
        )
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()
    
    # get the pending id and teacher chat id
    pending_id = int(query.data.split("#")[1])
    teacher_chat_id = int(query.data.split("#")[2])

    # save in context
    context.user_data["pending_answer"] = [pending_id, teacher_chat_id]

    # ask the student to send the answer or go back
    await query.edit_message_text(
        text=query.message.text + "\n\n" + "Envíe su respuesta o un archivo con más información.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
    )
    return states.S_SEND_ANSWER

async def student_send_answer(update: Update, context: ContextTypes):
    # get the pending id and teacher chat id
    pending_id, teacher_chat_id = context.user_data["pending_answer"]
    student_name = user_sql.get_user_by_chatid(update.effective_chat.id).fullname
    token_type = token_type_sql.get_token_type(pending_sql.get_pending(pending_id).token_type_id).type
    
    file = update.message.document or update.message.photo
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id
    else:
        fid = None

    answer_text = update.message.text or update.message.caption

    # update the pending
    if answer_text:
        text = f"> Respuesta de {student_name}:\n{answer_text}"
    else:   # if there is no text, send the file
        text = f"> {student_name} ha enviado un archivo."
    pending_sql.send_more_info(pending_id, text, fid)
    logger.info(f"Pending {pending_id} updated with more info from student.")
    # notify the teacher
    text = f"El estudiante {student_name} ha respondido a su solicitud de informacion sobre {token_type}, puede ver los detalles en pendientes."
    try:
        await context.bot.send_message(chat_id=teacher_chat_id, text=text)
    except BadRequest:
        logger.error(f"Error sending message to teacher {teacher_chat_id}.")
    await update.message.reply_text(
        "Su respuesta ha sido enviada al profesor.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, resize_keyboard=True, one_time_keyboard=True)
    )
    return ConversationHandler.END

async def student_answer_pending_back(update: Update, context: ContextTypes):
    """ Goes back to main menu. """
    query = update.callback_query
    query.answer()
    
    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_chat.id).id)
    classroom = classroom_sql.get_classroom(student.active_classroom_id)
    course_name = course_sql.get_course(classroom.course_id).name

    await query.message.edit_text(
        f"Menú principal de {user_sql.get_user_by_chatid(update.effective_chat.id).__name__}:\n\n"
        f"Curso: {course_name}\n"
        f"Aula: {classroom.name}",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, resize_keyboard=True, one_time_keyboard=True)
    )

    if "pending_answer" in context.user_data:
        context.user_data.pop("pending_answer")
    
    return ConversationHandler.END
    

# Handlers
student_answer_pending_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(student_answer_pending, pattern=r"^pending_more_info_student#")],
    states={
        states.S_SEND_ANSWER: [MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, student_send_answer)],
    },
    fallbacks=[
        CallbackQueryHandler(student_answer_pending_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_student_menu)
    ],
    # is a callbackqueryhandler it would be impossible to reenter at certain point if the user lost the message
)



