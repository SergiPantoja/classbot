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
from sql import user_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, student_sql, guild_token_sql, token_sql, student_token_sql, guild_sql, activity_type_sql, activity_sql
from bot.teacher_settings import back_to_teacher_menu


async def teacher_practic_classes(update: Update, context: ContextTypes):
    """ Shows the current practic classes.
        Button for creating new practic classes. 
     """
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
    
    # context vars
    context.user_data["practic_class"] = {}

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    # get all practic classes from db



async def teacher_practic_classes_back(update: Update, context: ContextTypes):
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

    if "practic_class" in context.user_data:
        context.user_data.pop("practic_class")
    return ConversationHandler.END


# Handlers

teacher_practic_classes_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("📔 Clases Prácticas"), teacher_practic_classes)],
    states={

    },
    fallbacks=[
        CallbackQueryHandler(teacher_practic_classes_back, pattern="back"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
    ],
    allow_reentry=True,
)
