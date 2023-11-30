import datetime

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
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
from sql import user_sql, teacher_sql, classroom_sql, course_sql, student_sql, student_classroom_sql, teacher_classroom_sql, conference_sql
from bot.student_inventory import back_to_student_menu


async def student_conferences(update: Update, context: ContextTypes):
    """ Sends a list of conferences belonging to the student current classrooms. """
    # get student
    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = student.active_classroom_id
    # get conferences
    conferences = conference_sql.get_conferences_by_classroom(classroom_id)
    if conferences:
        # show conferences with pagination, selecting a conference will show its details
        buttons = [InlineKeyboardButton(f"{i}. {conference.name} {datetime.date(conference.date.year, conference.date.month, conference.date.day)}", callback_data=f"conference#{conference.id}") for i, conference in enumerate(conferences, start=1)]
        await update.message.reply_text(
            "Conferencias:",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
        )
        return states.S_SELECT_CONFERENCE
    else:   # no conferences, return to student main menu
        await update.message.reply_text(
            "No hay conferencias disponibles en este momento.",
            reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
        return ConversationHandler.END

async def student_select_conference(update: Update, context: ContextTypes):
    query = update.callback_query
    query.answer()

    # get conference
    conference_id = int(query.data.split("#")[1])
    conference = conference_sql.get_conference(conference_id)
    # Show conference details
    if conference.fileID:
        try:
            await query.message.reply_photo(conference.fileID)
        except BadRequest:
            await query.message.reply_document(conference.fileID)
    await query.message.reply_text(
            f"Nombre: {conference.name}\n"
            f"Fecha: {datetime.date(conference.date.year, conference.date.month, conference.date.day)}\n",
            reply_markup=InlineKeyboardMarkup(keyboards.STUDENT_CONFERENCE_SELECTED)
        )
    return states.S_SELECT_CONFERENCE

async def student_conference_back(update: Update, context: ContextTypes):
    """ Returns to student menu """
    query = update.callback_query
    query.answer()

    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(student.active_classroom_id)
    course_name = course_sql.get_course(classroom.course_id).name

    await query.message.reply_text(
        f"Menú principal > {course_name} > {classroom.name}",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END


# Handlers
student_conferences_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Conferencias$"), student_conferences)],
    states={
        states.S_SELECT_CONFERENCE: [
            CallbackQueryHandler(student_select_conference, pattern="^conference#"),
            paginator_handler,
        ]
    },
    fallbacks=[
        CallbackQueryHandler(student_conference_back, pattern="^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_student_menu)
    ],
)
