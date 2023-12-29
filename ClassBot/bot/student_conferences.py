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
from bot.utils import states, keyboards, bot_text
from bot.utils.inline_keyboard_pagination import paginated_keyboard, paginator_handler
from bot.utils.clean_context import clean_student_context
from sql import user_sql, classroom_sql, course_sql, student_sql, conference_sql, pending_sql, token_type_sql
from bot.student_inventory import back_to_student_menu


async def student_conferences(update: Update, context: ContextTypes):
    """ Sends a list of conferences belonging to the student current classrooms. """
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
            "No tienes permiso para usar este comando.",
        )
        return ConversationHandler.END

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

    if query.data == "new_title_proposal":
        await query.edit_message_text(
            "Ingrese el nuevo título:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]])
        )
        return states.S_NEW_TITLE_PROPOSAL
    
    # get conference
    conference_id = int(query.data.split("#")[1])
    conference = conference_sql.get_conference(conference_id)
    # save conference id in context
    context.user_data["conference"] = {"id": conference_id}
    
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

async def student_new_title_proposal(update: Update, context: ContextTypes):
    # get necessary data
    user = user_sql.get_user_by_chatid(update.effective_user.id)
    student = student_sql.get_student(user.id)
    conference_id = context.user_data["conference"]["id"]
    conference = conference_sql.get_conference(conference_id)
    classroom_id = student.active_classroom_id
    token_type_id = token_type_sql.get_token_type_by_type("Propuesta de título").id
    text = f'{user.fullname}: Propone el título "{update.message.text}" para la conferencia {conference.name}.' 

    # create pending in database
    pending_sql.add_pending(student.id, classroom_id, token_type_id, text=text)
    logger.info(f"New title proposal by {user.fullname} for conference {conference.name}.")

    # send notification to notification channel of the classroom if it exists
    chan = classroom_sql.get_teacher_notification_channel_chat_id(classroom_id)
    if chan:
        try:
            await context.bot.send_message(
                chat_id=chan,
                text=f"Propuesta de título para la conferencia {conference.name}:\n"
                    f"{user.fullname}: Propone el título \"{update.message.text}\".",
            )
        except BadRequest:
            logger.exception(f"Failed to send message to notification channel {chan}.")

    # notify student that the proposal was sent
    await update.message.reply_text(
        "Propuesta enviada.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )

    # sanitize context
    if "conference" in context.user_data:
        context.user_data.pop("conference")
    return ConversationHandler.END
    
async def student_conference_back(update: Update, context: ContextTypes):
    """ Returns to student menu """
    query = update.callback_query
    query.answer()

    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(student.active_classroom_id)
    await query.message.reply_text(
        bot_text.main_menu(
            fullname=user_sql.get_user(student.id).fullname,
            role="student",
            classroom_name=classroom.name,
        ),
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="HTML",
    )
    # sanitize context
    if "conference" in context.user_data:
        context.user_data.pop("conference")
    return ConversationHandler.END


# Handlers
student_conferences_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^👨‍🏫 Conferencias$"), student_conferences)],
    states={
        states.S_SELECT_CONFERENCE: [
            CallbackQueryHandler(student_select_conference, pattern="^(conference#|new_title_proposal)"),
            paginator_handler,
        ],
        states.S_NEW_TITLE_PROPOSAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, student_new_title_proposal)]
    },
    fallbacks=[
        CallbackQueryHandler(student_conference_back, pattern="^back$"),
        MessageHandler(filters.Regex("^🔙$"), back_to_student_menu)
    ],
    allow_reentry=True,
)
