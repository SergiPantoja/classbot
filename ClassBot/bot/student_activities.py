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
from bot.utils.clean_context import clean_student_context
from sql import user_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, student_sql, guild_token_sql, token_sql, student_token_sql, guild_sql, activity_type_sql, activity_sql
from bot.student_inventory import back_to_student_menu


async def student_activities(update: Update, context: ContextTypes):
    """ Student activities menu. 
    Show the student's activities. 
    Initially individual activity_types that are not hidden. Options to 
    show activities from a guild. 
    """
    # sanitize context
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
    # context vars
    context.user_data["activity"] = {}

    query = update.callback_query
    if query:
        await query.answer()

    classroom_id = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_chat.id).id).active_classroom_id
    # get activity_types
    activity_types = activity_type_sql.get_activity_types(classroom_id)
    
    if query and query.data == "guild_activities":
        # filter by guild activities
        activity_types = [activity_type for activity_type in activity_types if activity_type.guild_activity]
    else: # if not query or query.data != "individual_activities":
        # filter by individual activities
        activity_types = [activity_type for activity_type in activity_types if not activity_type.guild_activity]
    
    if activity_types:
        # show activity_types with pagination
        buttons = [InlineKeyboardButton(f"{i}. {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"activity_type#{activity_type.id}") for i, activity_type in enumerate(activity_types, start=1)]
        other_buttons = [
            InlineKeyboardButton(f"{'Ver actividades individuales' if query and (query.data == 'guild_activities') else 'Ver actividades de gremio'}", callback_data="individual_activities" if query and (query.data == "guild_activities") else "guild_activities"),
        ]
        text = "Actividades de gremio" if query and (query.data == "guild_activities") else "Actividades individuales"
        if query:
            await query.edit_message_text(
                text,
                reply_markup=paginated_keyboard(buttons=buttons, context=context, add_back=True, other_buttons=other_buttons)
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=paginated_keyboard(buttons=buttons, context=context, add_back=True, other_buttons=other_buttons)
            )
    else:
        if query:
            await query.edit_message_text(
                "No hay actividades actualmente",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(f"{'Ver actividades individuales' if query.data == 'guild_activities' else 'Ver actividades de gremio'}", callback_data="individual_activities" if query.data == "guild_activities" else "guild_activities"),],
                        [InlineKeyboardButton("Atrás", callback_data="back")],
                    ]
                )
            )
        else:
            await update.message.reply_text(
                "No hay actividades actualmente",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Ver actividades de gremio", callback_data="guild_activities"),],
                        [InlineKeyboardButton("Atrás", callback_data="back")],
                    ]
                )
            )
    return states.S_ACTIVITY_TYPE_SELECT

async def activity_type_selected(update: Update, context: ContextTypes):
    pass

async def student_activities_back(update: Update, context: ContextTypes):
    """ Back to student menu. """
    query = update.callback_query
    await query.answer()

    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(student.active_classroom_id)
    course_name = course_sql.get_course(classroom.course_id).name

    await query.message.reply_text(
        f"Menú principal"
        f"Curso: {course_name}\n"
        f"Aula: {classroom.name}\n",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )

    if "activity" in context.user_data:
        context.user_data.pop("activity")
    return ConversationHandler.END


# Handlers

student_activities_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Actividades 📝$"), student_activities)],
    states={
        states.S_ACTIVITY_TYPE_SELECT: [
            CallbackQueryHandler(student_activities, pattern=r"^(individual_activities|guild_activities)$"),
            CallbackQueryHandler(activity_type_selected, pattern=r"^activity_type#"),
            paginator_handler,
        ],
    },
    fallbacks=[
        CallbackQueryHandler(student_activities_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_student_menu),
    ],
    allow_reentry=True,
)
