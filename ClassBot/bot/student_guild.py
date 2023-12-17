""" Just a way for students to see their guild."""

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
from sql import user_sql, teacher_sql, classroom_sql, course_sql, guild_sql, student_sql, student_guild_sql, guild_token_sql, pending_sql, token_type_sql, teacher_classroom_sql, token_sql, student_token_sql
from bot.student_inventory import back_to_student_menu


async def student_guild(update: Update, context: ContextTypes):
    """Shows the student's guilds"""
    # Sanitize context
    clean_student_context(context)

    # check role
    if "role" not in context.user_data:
        await update.message.reply_text(
            "La sesión ha expirado, por favor inicia sesión nuevamente",
            reply_markup=ReplyKeyboardMarkup(
                [["/start"]], resize_keyboard=True
            )
        )
        return 
    elif context.user_data["role"] != "student":
        await update.message.reply_text(
            "No tienes permiso para acceder a este comando",
        )
        return 
    
    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_chat.id).id)
    classroom_id = student.active_classroom_id
    # get the guilds of the classroom
    guilds = guild_sql.get_guilds_by_classroom(classroom_id)
    # check if the student is in a guild
    student_guild_ids = student_guild_sql.get_guild_ids(student.id)
    # get the guild of this classroom the student is in
    student_guild = None
    for guild in guilds:
        if guild.id in student_guild_ids:
            student_guild = guild
            break
    
    if student_guild:
        # get students in guild
        students = student_sql.get_students_by_guild(student_guild.id)
        student_text = "\n".join([f"{i}. {user_sql.get_user(student.id).fullname}" for i, student in enumerate(students, start=1)])
        text = f"Gremio: {guild.name}\n\nEstudiantes:\n{student_text}"
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(
                [["Atrás"]], one_time_keyboard=True, resize_keyboard=True
            )
        )
    else:
        await update.message.reply_text(
            "No estás en ningún gremio",
            reply_markup=ReplyKeyboardMarkup(
                [["Atrás"]], one_time_keyboard=True, resize_keyboard=True
            )
        )
            
student_guild_handler = MessageHandler(filters.Regex("^Gremio$"), student_guild)
