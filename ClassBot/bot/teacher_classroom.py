import datetime
from typing import TYPE_CHECKING

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
from bot.utils.clean_context import clean_teacher_context
from sql import user_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, student_sql, guild_token_sql, token_sql, student_token_sql, guild_sql, activity_type_sql, activity_sql, practic_class_sql, practic_class_exercises_sql
from bot.teacher_settings import back_to_teacher_menu


async def teacher_classroom(update: Update, context: ContextTypes):
    """ Teacher classroom menu. Here the teacher can see the classroom's students,
    guilds and send messages to all students in the classroom. """

    # sanitize context
    clean_teacher_context(context)

    # check user role
    if "role" not in context.user_data:
        await update.message.reply_text(
            "La sesión ha expirado, por favor inicia sesión nuevamente",
            reply_markup=ReplyKeyboardMarkup(
                [["/start"]], resize_keyboard=True
            )
        )
        return ConversationHandler.END
    elif context.user_data["role"] != "teacher":
        await update.message.reply_text(
            "No tienes permiso para acceder a este comando",
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Selecciona una opción",
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_CLASSROOM),
    )
    return states.T_CLASSROOM_OPTION

async def send_message(update: Update, context: ContextTypes):
    """ Sends a message to all students in the classroom. Supports sending
    photo or document as well."""
    query = update.callback_query
    await query.answer()

    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)

    await query.edit_message_text(
        f"Envía una notificación a todos los estudiantes de {classroom.name}.\n\nPuedes enviar un archivo o una foto, o simplemente un mensaje de texto.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
    )
    return states.T_CLASSROOM_SEND_MESSAGE

async def send_message_done(update: Update, context: ContextTypes):
    """ Receives the message to send to the students and sends it. """
    file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id

    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)

    teacher_name = user_sql.get_user(teacher.id).fullname
    text = f"<b>Mensaje de {teacher_name}:</b>\n<b>Aula - {classroom.name}</b>\n\n<i>{update.message.text if update.message.text else ''}</i>" + f"<i>{update.message.caption if update.message.caption else ''}</i>"

    # get students from db
    students = student_sql.get_students_by_classroom(classroom.id)

    # send message to all students
    for student in students:
        chat_id = user_sql.get_user(student.id).telegram_chatid
        try:
            if fid:
                try:
                    try:
                        await context.bot.send_photo(photo=fid, chat_id=chat_id, caption=text, parse_mode="HTML")
                    except BadRequest:
                        await context.bot.send_document(document=fid, chat_id=chat_id, caption=text, parse_mode="HTML")
                except BadRequest:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode="HTML",
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                )
        except BadRequest as e:
            logger.error(f"Error sending message to student {student.id}: {e}")
            await update.message.reply_text(
                f"Error enviando mensaje a {user_sql.get_user(student.id).fullname}",
            )
    
    await update.message.reply_text(
        "Mensajes enviados",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )

    return ConversationHandler.END


async def teacher_classroom_back(update: Update, context: ContextTypes):
    """ Go back to teacher main menu """
    query = update.callback_query
    await query.answer()

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    # get active classroom from db
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    # get course name
    course_name = course_sql.get_course(classroom.course_id).name

    await query.message.reply_text(
        f"Bienvenido profe {user_sql.get_user_by_chatid(update.effective_user.id).fullname}!\n\n"
        f"Curso: {course_name}\n"
        f"Aula: {classroom.name}\n"
        f"Menu en construcción...",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )

    if "classroom" in context.user_data:
        context.user_data.pop("classroom")
    return ConversationHandler.END


# Handlers
teacher_classroom_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(r"^🏫 Aula$"), teacher_classroom)],
    states={
        states.T_CLASSROOM_OPTION:[
            CallbackQueryHandler(send_message, pattern=r"^classroom_send_message$")
        ],
        states.T_CLASSROOM_SEND_MESSAGE:[MessageHandler(filters.TEXT | filters.Document.ALL | filters.PHOTO, send_message_done)],
    },
    fallbacks=[
        CallbackQueryHandler(teacher_classroom_back, pattern="back"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu),
    ],
    allow_reentry=True,
)


