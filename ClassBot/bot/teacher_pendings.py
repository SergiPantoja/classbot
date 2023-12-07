import datetime

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    filters,
)

from utils.logger import logger
from bot.utils import states, keyboards
from bot.utils.inline_keyboard_pagination import paginated_keyboard, paginator_handler
from bot.utils.pagination import Paginator, text_paginator_handler
from sql import user_sql, teacher_sql, classroom_sql, course_sql, conference_sql, pending_sql, token_type_sql, student_sql
from bot.teacher_settings import back_to_teacher_menu


async def teacher_pendings(update: Update, context: ContextTypes):
    """ Shows the pendings of the current classroom, except direct pendings.
    Shows options for filtering by pending type (token_type) or showing direct pendings.
    Enters the pendings conversation handler."""
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

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    # get the list of pendings of this classroom that are "PENDING" and not direct pendings
    pendings = pending_sql.get_pendings_by_classroom(classroom_id, status="PENDING")
    
    if pendings:
        # create a list of lines for each pending
        lines = [f"{i}. {token_type_sql.get_token_type(pending.token_type_id).type}: {user_sql.get_user(pending.student_id).fullname} Fecha: {datetime.date(pending.creation_date.year, pending.creation_date.month, pending.creation_date.day)} -> /pending_{pending.id}" for i, pending in enumerate(pendings, start=1)]
        # create new paginator using this lines
        other_buttons = [InlineKeyboardButton("Mis pendientes", callback_data="direct_pendings"), InlineKeyboardButton("Filtrar", callback_data="filter_pendings")]
        paginator = Paginator(lines, items_per_page=10, text_before="Pendientes del aula:", add_back=True, other_buttons=other_buttons)
        # save paginator in user_data
        context.user_data["paginator"] = paginator
        # send first page
        await update.message.reply_text(
            paginator.text(),
            reply_markup=paginator.keyboard()
        )
        return states.T_PENDING_SELECT

    else:   # no pendings, return to teacher main menu
        await update.message.reply_text(
            "No hay pendientes en este momento.",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
        return ConversationHandler.END
    


# Handlers
teacher_pendings_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Pendientes$"), teacher_pendings)],
    states={
        states.T_PENDING_SELECT: [
            text_paginator_handler,
            #CallbackQueryHandler(teacher_pendings, pattern=r"^direct_pendings$"),
            #CallbackQueryHandler(teacher_pendings, pattern=r"^filter_pendings$"),
            #CommandHandler(r"^pending_", pending_info),
        ],
        
    },
    fallbacks=[MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)],
)
