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
from sql import user_sql, student_sql, practic_class_sql, classroom_sql, course_sql, pending_sql, token_type_sql, teacher_classroom_sql, token_sql, student_token_sql, conference_sql, activity_type_sql
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
    return states.S_ACTIONS_SELECT_ACTION

async def select_action(update: Update, context: ContextTypes):
    """Selects the student action"""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "action_class_intervention":
        await query.edit_message_text(
            "Seleccione la clase en la que desea intervenir",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Conferencias", callback_data="select_intervention:conference"), InlineKeyboardButton("Clases Prácticas", callback_data="select_intervention:practic_class")],
                    [InlineKeyboardButton("Atrás", callback_data="back")],
                ]
            )
        )
        return states.S_ACTIONS_SELECT_INTERVENTION
    if action == "action_teacher_correction":
        """ Shows the teachers of the classroom to select """
        student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
        classroom = classroom_sql.get_classroom(student.active_classroom_id)
        teacher_ids = teacher_classroom_sql.get_teacher_ids(classroom.id)
        if teacher_ids:
            buttons = [InlineKeyboardButton(f"{i}. {user_sql.get_user(teacher_id).fullname}", callback_data=f"teacher#{teacher_id}") for i, teacher_id in enumerate(teacher_ids, start=1)]
            await query.edit_message_text(
                "Seleccione el profesor al que desea rectificar",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True)
            )
            return states.S_ACTIONS_SEND_RECTIFICATION   # paginator works?
        else:
            await query.edit_message_text(
                "No hay profesores en esta aula",
                reply_markup=InlineKeyboardMarkup(keyboards.STUDENT_ACTIONS),
            )
            return states.S_ACTIONS_SELECT_ACTION
    if action == "action_status_phrase":
        await query.edit_message_text(
            "Envíe un mensaje con su nueva frase de estado",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.S_ACTIONS_SEND_STATUS_PHRASE
    if action == "action_diary_update":
        # diary can only be updated once a day
        # so first check if the student has already updated his diary today
        student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
        # get the last diary update
        last_diary_update = pending_sql.get_last_pending_of_student_by_type(student.id, student.active_classroom_id, token_type_sql.get_token_type_by_type("Actualización de diario").id)
        if last_diary_update:
            # if the last diary update was less than 1 day ago then don't allow to update again
            if datetime.datetime.now() - last_diary_update.creation_date < datetime.timedelta(days=1):
                print(datetime.datetime.now())
                print(last_diary_update.creation_date)
                print(datetime.datetime.now() - last_diary_update.creation_date)
                await query.edit_message_text(
                    "Ya has actualizado tu diario hoy",
                    reply_markup=InlineKeyboardMarkup(keyboards.STUDENT_ACTIONS),
                )
                return states.S_ACTIONS_SELECT_ACTION
            # else proceed
            else:
                await query.edit_message_text(
                    "Envíe un mensaje con su actualización de diario",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
                )
                return states.S_ACTIONS_SEND_DIARY_UPDATE
        else:
            # no diary update yet then proceed
            await query.edit_message_text(
                "Envíe un mensaje con su actualización de diario",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
            )
            return states.S_ACTIONS_SEND_DIARY_UPDATE   
    if action == "action_meme":
        await query.edit_message_text(
            "Envíe una imagen con su meme.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.S_ACTIONS_SEND_MEME
    if action == "action_joke":
        await query.edit_message_text(
            "Envíe un mensaje con su chiste.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.S_ACTIONS_SEND_JOKE
    if action == "action_misc":
        await query.edit_message_text(
            "Envíe un mensaje con la miscelánea que desea proponer",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.S_ACTIONS_SEND_MISC
    
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
        "Miscelánea enviada.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )
    return ConversationHandler.END

async def select_intervention(update: Update, context: ContextTypes):
    """ shows the conferences or the practic classes for the student to select """
    query = update.callback_query
    await query.answer()

    if query.data.startswith("select_intervention:"):
        intervention_type = query.data.split(":")[1]
        classroom_id = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id

        if intervention_type == "conference":
            conferences = conference_sql.get_conferences_by_classroom(classroom_id)
            if not conferences:
                await query.edit_message_text(
                    "No hay conferencias en esta aula",
                    reply_markup=InlineKeyboardMarkup(keyboards.STUDENT_ACTIONS),
                )
                return states.S_ACTIONS_SELECT_ACTION
            buttons = [InlineKeyboardButton(f"{i}. {conference.name} - {datetime.date(conference.date.year, conference.date.month, conference.date.day)}", callback_data=f"conference#{conference.id}") for i, conference in enumerate(conferences, start=1)]
            await query.edit_message_text(
                "Seleccione la conferencia en la que desea intervenir",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True)
            )
            return states.S_ACTIONS_SELECT_INTERVENTION

        elif intervention_type == "practic_class":
            practic_classes = practic_class_sql.get_practic_classes(classroom_id=classroom_id, include_hidden=True)
            if not practic_classes:
                await query.edit_message_text(
                    "No hay clases prácticas en esta aula",
                    reply_markup=InlineKeyboardMarkup(keyboards.STUDENT_ACTIONS),
                )
                return states.S_ACTIONS_SELECT_ACTION
            buttons = [InlineKeyboardButton(f"{i}. {token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class.activity_type_id).token_type_id).type} - {datetime.date(practic_class.date.year, practic_class.date.month, practic_class.date.day)}", callback_data=f"practic_class#{practic_class.id}") for i, practic_class in enumerate(practic_classes, start=1)]
            await query.edit_message_text(
                "Seleccione la clase práctica en la que desea intervenir",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True)
            )
            return states.S_ACTIONS_SELECT_INTERVENTION

    elif query.data.startswith("conference#"):
        if "intervention" not in context.user_data:
            context.user_data["intervention"] = {
                "conference_id": int(query.data.split("#")[1])
            }
        await query.edit_message_text(
            "Envíe un mensaje con los detalles de su intervención",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.S_ACTIONS_SEND_INTERVENTION

    elif query.data.startswith("practic_class#"):
        if "intervention" not in context.user_data:
            context.user_data["intervention"] = {
                "practic_class_id": int(query.data.split("#")[1])
            }
        await query.edit_message_text(
            "Envíe un mensaje con los detalles de su intervención",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.S_ACTIONS_SEND_INTERVENTION
async def send_intervention(update: Update, context: ContextTypes):
    """ Creates a new intervention pending """
    # get necessary data
    user = user_sql.get_user_by_chatid(update.effective_user.id)
    student = student_sql.get_student(user.id)
    classroom_id = student.active_classroom_id
    token_type_id = token_type_sql.get_token_type_by_type("Intervención en clase").id

    if "conference_id" in context.user_data["intervention"]:
        conference = conference_sql.get_conference(context.user_data["intervention"]["conference_id"])
        text = f"{user.fullname} ha intervenido en la conferencia {conference.name}:\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"
    elif "practic_class_id" in context.user_data["intervention"]:
        practic_class = practic_class_sql.get_practic_class(context.user_data["intervention"]["practic_class_id"])
        text = f"{user.fullname} ha intervenido en la clase práctica {token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class.activity_type_id).token_type_id).type}:\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"

    # create pending in database
    pending_sql.add_pending(student.id, classroom_id, token_type_id, text=text)
    logger.info(f"New intervention by {user.fullname}.")
    #TODO send notification to notification channel of the classroom if it exists

    # notify student that the proposal was sent
    await update.message.reply_text(
        "Intervención enviada.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )
    return ConversationHandler.END

async def send_rectification(update: Update, context: ContextTypes):
    query = update.callback_query
    
    if query:
        await query.answer()
        teacher_id = int(query.data.split("#")[1])
        # save teacher_id in context.user_data
        if "rectification" not in context.user_data:
            context.user_data["rectification"] = {
                "teacher_id": teacher_id
            }
        await query.edit_message_text(
            f"Escriba su rectificación al profesor {user_sql.get_user(teacher_id).fullname}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.S_ACTIONS_SEND_RECTIFICATION
    else:
        # get necessary data
        user = user_sql.get_user_by_chatid(update.effective_user.id)
        student = student_sql.get_student(user.id)
        classroom_id = student.active_classroom_id
        token_type_id = token_type_sql.get_token_type_by_type("Rectificación al profesor").id
        teacher_id = context.user_data["rectification"]["teacher_id"]

        text = f"{user.fullname} ha rectificado al profesor {user_sql.get_user(teacher_id).fullname}:\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"

        # create pending in database
        pending_sql.add_pending(student.id, classroom_id, token_type_id, teacher_id=teacher_id, text=text)
        logger.info(f"New rectification by {user.fullname}.")
        #TODO send notification to notification channel of the classroom if it exists

        # notify this teacher that he has a new rectification in his direct pendings
        teacher_chat_id = user_sql.get_user(teacher_id).telegram_chatid
        if teacher_chat_id:
            try:
                await context.bot.send_message(
                    teacher_chat_id,
                    f"Tienes una nueva rectificación de {user.fullname} en tu lista de pendientes directos",
                    reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
                )
            except BadRequest:
                logger.exception(f"Failed to send message to teacher {teacher_id}.")

        # notify student that the proposal was sent
        await update.message.reply_text(
            "Rectificación enviada.",
            reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
        )
        return ConversationHandler.END

async def send_status_phrase(update: Update, context: ContextTypes):
    """ Creates a new status phrase pending """
    # get necessary data
    user = user_sql.get_user_by_chatid(update.effective_user.id)
    student = student_sql.get_student(user.id)
    classroom_id = student.active_classroom_id
    token_type_id = token_type_sql.get_token_type_by_type("Frase de estado").id

    text = f"{user.fullname} ha cambiado su frase de estado:\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"

    # create pending in database
    pending_sql.add_pending(student.id, classroom_id, token_type_id, text=text)
    logger.info(f"New status phrase by {user.fullname}.")
    #TODO send notification to notification channel of the classroom if it exists

    # notify student that the proposal was sent
    await update.message.reply_text(
        "Frase de estado actualizada.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )
    return ConversationHandler.END

async def send_meme(update: Update, context: ContextTypes):
    """ Creates a new meme pending """
    # get necessary data
    user = user_sql.get_user_by_chatid(update.effective_user.id)
    student = student_sql.get_student(user.id)
    classroom_id = student.active_classroom_id
    token_type_id = token_type_sql.get_token_type_by_type("Meme").id

    # get file id if exists
    file = update.message.photo
    if not file:
        await update.message.reply_text(
            "No se ha enviado una imagen",
            reply_markup=InlineKeyboardMarkup(keyboards.STUDENT_ACTIONS),
        )
        return states.S_ACTIONS_SELECT_ACTION

    text = f"{user.fullname} ha enviado un meme:\n" + f"{update.message.caption if update.message.caption else ''}"

    # create pending in database
    pending_sql.add_pending(student.id, classroom_id, token_type_id, text=text, FileID=file[-1].file_id)
    logger.info(f"New meme by {user.fullname}.")
    #TODO send notification to notification channel of the classroom if it exists

    # notify student that the proposal was sent
    await update.message.reply_text(
        "Meme enviado.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )
    return ConversationHandler.END

async def send_joke(update: Update, context: ContextTypes):
    """ Creates a new joke pending """
    # get necessary data
    user = user_sql.get_user_by_chatid(update.effective_user.id)
    student = student_sql.get_student(user.id)
    classroom_id = student.active_classroom_id
    token_type_id = token_type_sql.get_token_type_by_type("Chiste").id

    text = f"{user.fullname} ha enviado un chiste:\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"

    # create pending in database
    pending_sql.add_pending(student.id, classroom_id, token_type_id, text=text)
    logger.info(f"New joke by {user.fullname}.")
    #TODO send notification to notification channel of the classroom if it exists

    # notify student that the proposal was sent
    await update.message.reply_text(
        "Chiste enviado.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )
    return ConversationHandler.END

async def send_diary_update(update: Update, context: ContextTypes):
    """ Creates a new diary update pending """
    # get necessary data
    user = user_sql.get_user_by_chatid(update.effective_user.id)
    student = student_sql.get_student(user.id)
    classroom_id = student.active_classroom_id
    token_type_id = token_type_sql.get_token_type_by_type("Actualización de diario").id

    text = f"{user.fullname} ha actualizado su diario:\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"

    # create pending in database
    pending_sql.add_pending(student.id, classroom_id, token_type_id, text=text)
    logger.info(f"New diary update by {user.fullname}.")
    #TODO send notification to notification channel of the classroom if it exists

    # notify student that the proposal was sent
    await update.message.reply_text(
        "Actualización de diario enviada.",
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
        states.S_ACTIONS_SELECT_ACTION: [CallbackQueryHandler(select_action, pattern=r"^action_")],
        states.S_ACTIONS_SEND_MISC: [MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, send_misc)],
        states.S_ACTIONS_SELECT_INTERVENTION: [
            CallbackQueryHandler(select_intervention, pattern=r"^(select_intervention:|conference#|practic_class#)"),
            paginator_handler,
        ],
        states.S_ACTIONS_SEND_INTERVENTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_intervention)],
        states.S_ACTIONS_SEND_RECTIFICATION: [
            CallbackQueryHandler(send_rectification, pattern=r"^teacher#"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, send_rectification),
            paginator_handler,
        ],
        states.S_ACTIONS_SEND_STATUS_PHRASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_status_phrase)],
        states.S_ACTIONS_SEND_MEME: [MessageHandler(filters.PHOTO & ~filters.COMMAND, send_meme)],
        states.S_ACTIONS_SEND_JOKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_joke)],
        states.S_ACTIONS_SEND_DIARY_UPDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_diary_update)],
    },
    fallbacks=[
        CallbackQueryHandler(student_actions_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_student_menu)
    ],
    allow_reentry=True,
)
