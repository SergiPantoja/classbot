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
from bot.teacher_settings import back_to_teacher_menu


async def teacher_conferences(update: Update, context: ContextTypes):
    """Shows conferences of the classroom if any, else prompts user to create one"""
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    conferences = conference_sql.get_conferences_by_classroom(classroom_id)
    if conferences:
        # Show all conferences with pagination, selecting a conference will allow
        # the user to edit or delete it, also create a new conference button.
        buttons = [InlineKeyboardButton(f"{i}. {conference.name} {datetime.date(conference.date.year, conference.date.month, conference.date.day)}", callback_data=f"conference#{conference.id}") for i, conference in enumerate(conferences, start=1)]
        other_buttons = [InlineKeyboardButton("Crear conferencia", callback_data="conference_create")]
        await update.message.reply_text(
            "Conferencias del aula",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons)
        )
        return states.T_SELECT_CONFERENCE
    else:
        # No conferences, ask to create one first
        await update.message.reply_text(
            "No hay conferencias registradas. Por favor crea una primero.",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_CONFERENCE_CREATE)
        )
        return states.T_CREATE_CONFERENCE

async def teacher_create_conference(update: Update, context:ContextTypes):
    """ Create new conference """
    # add conference to user context
    context.user_data["conference"] = {}
    # ask for conference name
    query = update.callback_query
    query.answer()
    await query.message.reply_text(
        "Ingresa el nombre de la conferencia",
        reply_markup=ReplyKeyboardRemove()
    )
    return states.T_CREATE_CONFERENCE_NAME

async def teacher_create_conference_name(update: Update, context: ContextTypes):
    """ Get conference name """
    # add conference name to user context
    context.user_data["conference"]["name"] = update.message.text
    # ask for conference date
    await update.message.reply_text(
        "Ingresa la fecha de la conferencia en este formato: dd-mm-aaaa",
        reply_markup=ReplyKeyboardRemove()
    )
    return states.T_CREATE_CONFERENCE_DATE

async def teacher_create_conference_date(update: Update, context: ContextTypes):
    """ Get conference date """
    date_str = update.message.text
    try:
        date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        await update.message.reply_text(
            "Formato de fecha inválido, por favor ingresa la fecha en este formato: dd-mm-aaaa",
            reply_markup=ReplyKeyboardRemove()
        )
        return states.T_CREATE_CONFERENCE_DATE
    # add conference date to user context
    context.user_data["conference"]["date"] = date
    # ask for conference resources like an image or a pdf
    await update.message.reply_text(
        "Envie documentos de la conferencia (imagen o pdf) o presione crear.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Crear", callback_data="conference_done")]])
    )
    return states.T_CREATE_CONFERENCE_FILE

async def teacher_create_conference_file(update: Update, context: ContextTypes):
    """ Creates the conference with the fileID of the sent file or without if no file is sent """
    if update.message: # user sent a message with probably a file.
        file = update.message.document or update.message.photo
        if file:
            if update.message.document:
                fid = file.file_id
            else:
                fid = file[-1].file_id
            context.user_data["conference"]["file_id"] = fid
    # get conference data from user context
    name = context.user_data["conference"]["name"]
    date = context.user_data["conference"]["date"]
    file_id = context.user_data["conference"].get("file_id", None)
    # get classroom id
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    # add conference to database
    conference_sql.add_conference(classroom_id, name, date, file_id)
    # clear user context
    context.user_data.pop("conference")

    # show conferences
    conferences = conference_sql.get_conferences_by_classroom(classroom_id)
    buttons = [InlineKeyboardButton(f"{i}. {conference.name}, {datetime.date(conference.date.year, conference.date.month, conference.date.day)}", callback_data=f"conference#{conference.id}") for i, conference in enumerate(conferences, start=1)]
    other_buttons = [InlineKeyboardButton("Crear conferencia", callback_data="conference_create")]
    query = update.callback_query
    if query:
        query.answer()
        await query.message.reply_text(
            "Conferencias del aula",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons)
        )
    else:
        await update.message.reply_text(
            "Conferencias del aula",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons)
        )
    return states.T_SELECT_CONFERENCE

async def teacher_conference_select(update: Update, context: ContextTypes):
    """ Selects a conference to edit or delete """
    query = update.callback_query
    query.answer()
    
    if query.data == "conference_create":
        logger.info("Creating conference...")
        context.user_data["conference"] = {}
        await query.message.reply_text(
            "Ingresa el nombre de la conferencia",
            reply_markup=ReplyKeyboardRemove()
        )
        return states.T_CREATE_CONFERENCE_NAME
    else:
        logger.info("Selecting conference...")
        conference_id = int(query.data.split("#")[1])
        # save id in user context
        context.user_data["conference"] = {"id": conference_id}
        # get conference from db
        conference = conference_sql.get_conference(conference_id)
        # show conference info and send photo or document
        # use try-except to send photo if BadRequest send document 
        if conference.fileID:
            try:
                await query.message.reply_photo(conference.fileID)
            except BadRequest:
                await query.message.reply_document(conference.fileID)
        await query.message.reply_text(
                f"Nombre: {conference.name}\n"
                f"Fecha: {datetime.date(conference.date.year, conference.date.month, conference.date.day)}\n",
                reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_CONFERENCE_EDIT)
            )
        return states.T_CONFERENCE_EDIT_OPTION

async def teacher_conference_edit_option(update: Update, context: ContextTypes):
    """ Edits or deletes a conference """
    query = update.callback_query
    query.answer()

    if query.data == "conference_edit_name":
        logger.info("Editing conference name...")
        # ask for new name
        await query.message.reply_text(
            "Ingresa el nuevo nombre de la conferencia",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="conference_back")]])
        )
        return states.T_EDIT_CONFERENCE_NAME
    elif query.data == "conference_edit_date":
        logger.info("Editing conference date...")
        # ask for new date
        await query.message.reply_text(
            "Ingresa la nueva fecha de la conferencia en este formato: dd-mm-aaaa",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="conference_back")]])
        )
        return states.T_EDIT_CONFERENCE_DATE
    elif query.data == "conference_edit_file":
        logger.info("Editing conference file...")
        # ask for new file
        await query.message.reply_text(
            "Envie documentos de la conferencia (imagen o pdf).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="conference_back")]])
        )
        return states.T_EDIT_CONFERENCE_FILE
    elif query.data == "conference_edit_delete":
        logger.info("Deleting conference...")
        # get conference id
        conference_id = context.user_data["conference"]["id"]
        # delete conference from db
        conference_sql.delete_conference(conference_id)
        # get back to main menu
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
        if "conference" in context.user_data:
            context.user_data.pop("conference")
        return ConversationHandler.END
    
async def teacher_conference_edit_name(update: Update, context: ContextTypes):
    """ Edits conference name """
    # get conference id
    conference_id = context.user_data["conference"]["id"]
    # get conference from db
    conference = conference_sql.get_conference(conference_id)
    # update conference name
    conference_sql.update_conference_name(conference_id, name=update.message.text)
    # show conference info and send photo or document
    # use try-except to send photo if BadRequest send document 
    if conference.fileID:
        try:
            await update.message.reply_photo(conference.fileID)
        except BadRequest:
            await update.message.reply_document(conference.fileID)
    await update.message.reply_text(
            f"Nombre: {conference_sql.get_conference(conference_id).name}\n"
            f"Fecha: {datetime.date(conference.date.year, conference.date.month, conference.date.day)}\n",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_CONFERENCE_EDIT)
        )
    return states.T_CONFERENCE_EDIT_OPTION

async def teacher_conference_edit_date(update: Update, context: ContextTypes):
    """ Edits conference date """
    # get conference id
    conference_id = context.user_data["conference"]["id"]
    # get conference from db
    conference = conference_sql.get_conference(conference_id)
    # update conference date
    date_str = update.message.text
    try:
        date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        await update.message.reply_text(
            "Formato de fecha inválido, por favor ingresa la fecha en este formato: dd-mm-aaaa",
            reply_markup=ReplyKeyboardRemove()
        )
        return states.T_EDIT_CONFERENCE_DATE
    conference_sql.update_conference_date(conference_id, date=date)
    conference = conference_sql.get_conference(conference_id)
    # show conference info and send photo or document
    # use try-except to send photo if BadRequest send document 
    if conference.fileID:
        try:
            await update.message.reply_photo(conference.fileID)
        except BadRequest:
            await update.message.reply_document(conference.fileID)
    await update.message.reply_text(
            f"Nombre: {conference.name}\n"
            f"Fecha: {datetime.date(conference.date.year, conference.date.month, conference.date.day)}\n",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_CONFERENCE_EDIT)
        )
    return states.T_CONFERENCE_EDIT_OPTION

async def teacher_conference_edit_file(update: Update, context: ContextTypes):
    """ Edits conference file """
    # get conference id
    conference_id = context.user_data["conference"]["id"]
    # get conference from db
    conference = conference_sql.get_conference(conference_id)
    # update conference file
    file = update.message.document or update.message.photo
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id
        conference_sql.update_conference_fileID(conference_id, fileID=fid)
    conference = conference_sql.get_conference(conference_id)
    # show conference info and send photo or document
    # use try-except to send photo if BadRequest send document 
    if conference.fileID:
        try:
            await update.message.reply_photo(conference.fileID)
        except BadRequest:
            await update.message.reply_document(conference.fileID)
    await update.message.reply_text(
            f"Nombre: {conference.name}\n"
            f"Fecha: {datetime.date(conference.date.year, conference.date.month, conference.date.day)}\n",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_CONFERENCE_EDIT)
        )
    return states.T_CONFERENCE_EDIT_OPTION


async def teacher_conference_back(update: Update, context: ContextTypes):
    """Returns to the teacher menu"""
    query = update.callback_query
    query.answer()

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

    if "conference" in context.user_data:
        context.user_data.pop("conference")
    
    return ConversationHandler.END


# Handlers
teacher_conferences_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Conferencias del aula$"), teacher_conferences)],
    states={
        states.T_CREATE_CONFERENCE: [CallbackQueryHandler(teacher_create_conference, pattern=r"^conference_create$")],
        states.T_CREATE_CONFERENCE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_create_conference_name)],
        states.T_CREATE_CONFERENCE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_create_conference_date)],
        states.T_CREATE_CONFERENCE_FILE: [
            MessageHandler(filters.PHOTO | filters.Document.ALL , teacher_create_conference_file),
            CallbackQueryHandler(teacher_create_conference_file, pattern=r"^conference_done$"),
            ],
        states.T_SELECT_CONFERENCE: [
            CallbackQueryHandler(teacher_conference_select, pattern=r"^(conference#|conference_create)"),
            paginator_handler
            ],
        states.T_CONFERENCE_EDIT_OPTION: [CallbackQueryHandler(teacher_conference_edit_option, pattern=r"^conference_edit_")],
        states.T_EDIT_CONFERENCE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_conference_edit_name)],
        states.T_EDIT_CONFERENCE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_conference_edit_date)],
        states.T_EDIT_CONFERENCE_FILE: [MessageHandler(filters.PHOTO | filters.Document.ALL , teacher_conference_edit_file)],
    },
    fallbacks=[
        CallbackQueryHandler(teacher_conference_back, pattern=r"^(conference_back|back)$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
        ],
)
