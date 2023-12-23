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
from sql import user_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, student_sql, guild_token_sql, token_sql, student_token_sql, guild_sql, activity_type_sql, activity_sql, practic_class_sql, practic_class_exercises_sql
from bot.student_inventory import back_to_student_menu


async def student_practic_classes(update: Update, context: ContextTypes):
    """ Student practic classes menu. 
        Show a list of practic classes belonging to the student current classroom.
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
    context.user_data["practic_class"] = {}

    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    practic_classes = practic_class_sql.get_practic_classes(classroom_id=student.active_classroom_id, include_hidden=True)

    if practic_classes:
        # show practic classes with pagination
        buttons = [InlineKeyboardButton(f"{i}. {token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class.activity_type_id).token_type_id).type} - {datetime.date(practic_class.date.year, practic_class.date.month, practic_class.date.day)}", callback_data=f"practic_class#{practic_class.id}") for i, practic_class in enumerate(practic_classes, start=1)]
        await update.message.reply_text(
            "Clases prácticas:",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
        )
        return states.S_SELECT_PRACTIC_CLASS
    else:
        await update.message.reply_text(
            "No hay clases prácticas disponibles en este momento.",
            reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
        return ConversationHandler.END

async def practic_class_selected(update: Update, context: ContextTypes):
    """ Show the details of the selected practic class.
        Show exercises with pagination.
        Show a button to send a new title proposal.
    """
    query = update.callback_query
    await query.answer()

    # save practic class in context
    if "practic_class_id" in context.user_data["practic_class"]:
        practic_class_id = context.user_data["practic_class"]["practic_class_id"]
    else:
        practic_class_id = int(query.data.split("#")[1])
        context.user_data["practic_class"]["practic_class_id"] = practic_class_id

    if query.data == "new_title_proposal":
        if query.message.caption:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\nIngrese el nuevo título:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
            )
        else:
            await query.edit_message_text(
                query.message.text + "\n\nIngrese el nuevo título:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
            )
        return states.S_PRACTIC_CLASS_NEW_TITLE_PROPOSAL
    
    practic_class = practic_class_sql.get_practic_class(practic_class_id)
    activity_type = activity_type_sql.get_activity_type(practic_class.activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    # show practic class details
    text = f"<b>Clase práctica:</b> {token_type.type}\n"
    text += f"<b>Fecha:</b> {practic_class.date.strftime('%d-%m-%Y')}\n"
    if activity_type.description:
        text += f"<b>Descripción:</b> {activity_type.description}\n"
    text += "<b>Ejercicios:</b>\n"
    exercises = practic_class_exercises_sql.get_practic_class_exercises_by_practic_class_id(practic_class_id)
    # dont show exercises the student has earned credits for
    exercises = [exercise for exercise in exercises if not student_token_sql.exists(student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id).id, token_sql.get_token(activity_sql.get_activity(exercise.activity_id).token_id).id)]
    if exercises:
        # sort exercises by name
        exercises.sort(key=lambda x: token_sql.get_token(activity_sql.get_activity(x.activity_id).token_id).name)
        buttons = [InlineKeyboardButton(f"{i}. {token_sql.get_token(activity_sql.get_activity(exercise.activity_id).token_id).name} - ({exercise.value})", callback_data=f"exercise#{exercise.id}") for i, exercise in enumerate(exercises, start=1)]    
        other_buttons = [
            InlineKeyboardButton("Proponer nuevo título", callback_data="new_title_proposal"),
        ]
        if activity_type.FileID:
            try:
                try:
                    await query.message.reply_photo(activity_type.FileID, caption=text, parse_mode="HTML", reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
                except BadRequest:
                    await query.message.reply_document(activity_type.FileID, caption=text, parse_mode="HTML", reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
            except BadRequest:
                await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar la clase práctica para enviar otro archivo.\n\n" + text, parse_mode="HTML", reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
        else:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
        return states.S_EXERCISE_SELECT
    else:
        text += "No hay ejercicios disponibles en este momento."
        if activity_type.FileID:
            try:
                try:
                    await query.message.reply_photo(activity_type.FileID, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Proponer nuevo título", callback_data="new_title_proposal")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
                except BadRequest:
                    await query.message.reply_document(activity_type.FileID, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Proponer nuevo título", callback_data="new_title_proposal")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
            except BadRequest:
                await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar la clase práctica para enviar otro archivo.\n\n" + text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Proponer nuevo título", callback_data="new_title_proposal")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
        else:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Proponer nuevo título", callback_data="new_title_proposal")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
        return states.S_SELECT_PRACTIC_CLASS

async def practic_class_new_title_proposal(update: Update, context: ContextTypes):
    """ Register a new title proposal for the selected practic class. """
    # get necessary data
    user = user_sql.get_user_by_chatid(update.effective_user.id)
    student = student_sql.get_student(user.id)
    practic_class_id = context.user_data["practic_class"]["practic_class_id"]
    practic_class = practic_class_sql.get_practic_class(practic_class_id)
    token_type_id = token_type_sql.get_token_type_by_type("Propuesta de título").id
    text = f'{user.fullname}: Propone el título "{update.message.text}" para la clase práctica "{token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class.activity_type_id).token_type_id).type}"' 

    # create pending in database
    pending_sql.add_pending(student.id, student.active_classroom_id, token_type_id, text=text)
    logger.info(f"New title proposal for practic class {practic_class_id} by {user.fullname}")
    # send notification to notification channel of the classroom if it exists
    #TODO

    # notify student that the proposal was sent
    await update.message.reply_text(
        "Propuesta enviada.",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )
    #sanitized context
    if "practic_class" in context.user_data:
        context.user_data.pop("practic_class")
    return ConversationHandler.END

async def practic_class_exercise_selected(update: Update, context: ContextTypes):
    """ Show the details of the selected exercise. 
        Button to send a new submission.
        If a pending/submission exists (but havent been reviewed yet), notify
        the student and ask if he wants to update his submission. (which will
        delete the previous submission and create a new one)
    """
    query = update.callback_query
    await query.answer()

    exercise_id = int(query.data.split("#")[1])
    context.user_data["practic_class"]["exercise_id"] = exercise_id
    exercise = practic_class_exercises_sql.get_practic_class_exercise(exercise_id)
    activity = activity_sql.get_activity(exercise.activity_id)
    token = token_sql.get_token(activity.token_id)
    practic_class = practic_class_sql.get_practic_class(exercise.practic_class_id)
    activity_type = activity_type_sql.get_activity_type(practic_class.activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    text = f"Ejercicio: <b>{token.name}</b> de la clase práctica <b>{token_type.type}</b>\n"
    text += f"Valor: <b>{exercise.value}</b>\n"
    if token.description:
        text += f"Descripción: <b>{token.description}</b>\n"

    if activity.FileID:
        try:
            try:
                await query.message.reply_photo(activity.FileID, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Enviar solución", callback_data="send_submission")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
            except BadRequest:
                await query.message.reply_document(activity.FileID, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Enviar solución", callback_data="send_submission")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
        except BadRequest:
            await query.edit_message_text("Se ha producido un error al enviar el archivo.\n\n" + text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Enviar solución", callback_data="send_submission")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
    else:
        if query.message.caption:
            await query.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Enviar solución", callback_data="send_submission")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
        else:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Enviar solución", callback_data="send_submission")], [InlineKeyboardButton("Atrás", callback_data="back")]]))
    return states.S_EXERCISE_SEND_SUBMISSION

async def practic_class_exercise_send_submission(update: Update, context: ContextTypes):
    """ Asks for the submission info. """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(query.message.caption + "\n\nEnvía tu solución. Puedes enviar texto, una imagen o un archivo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),)
    else:
        await query.edit_message_text(query.message.text + "\n\nEnvía tu solución. Puedes enviar texto, una imagen o un archivo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),)
    return states.S_EXERCISE_SEND_SUBMISSION_DONE

async def practic_class_exercise_send_submission_done(update: Update, context: ContextTypes):
    """ Creates a pending of token_type of the activity_type of the practic class
    and token of the activity of the exercise. 
    If a pending with this token already exists, notify the student and ask if he
    wants to update his submission. (which will delete the previous submission
    and create a new one)
    """
    query = update.callback_query
    if query:
        await query.answer()

    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = student.active_classroom_id
    exercise_id = context.user_data["practic_class"]["exercise_id"]
    practic_class_id = context.user_data["practic_class"]["practic_class_id"]
    practic_class = practic_class_sql.get_practic_class(practic_class_id)
    activity_type = activity_type_sql.get_activity_type(practic_class.activity_type_id)
    exercise = practic_class_exercises_sql.get_practic_class_exercise(exercise_id)
    activity = activity_sql.get_activity(exercise.activity_id)
    token = token_sql.get_token(activity.token_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    if not query:
        # get file id if exists
        file = update.message.document or update.message.photo
        fid = None
        if file:
            if update.message.document:
                fid = file.file_id
            else:
                fid = file[-1].file_id
        context.user_data["practic_class"]["file_id"] = fid

        text = f"{user_sql.get_user(student.id).fullname} ha enviado una entrega para el ejercicio {token.name} de la clase práctica {token_type.type}:\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"
        context.user_data["practic_class"]["text"] = text

    # check if a pending with this token already exists
    pending = pending_sql.get_pending_of_student_by_token(student.id, classroom_id, token.id)
    if pending:
        # notify the student a submission already exists and ask if he wants to update it
        # (will delete the old pending and return to this state)
        if query: # delete pending
            pending_sql.delete_pending(pending.id)
            logger.info(f"Pending {pending.id} deleted")
        else:
            await update.message.reply_text(
                "Ya has enviado una solución para este ejercicio. ¿Deseas actualizarla?",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Sí", callback_data="delete_pending")], [InlineKeyboardButton("No", callback_data="back")]]),
            )
            return states.S_EXERCISE_SEND_SUBMISSION_DONE
    
    # create pending in database
    pending_sql.add_pending(student.id, classroom_id, token_type_id=activity_type.token_type_id, token_id=token.id, text=context.user_data["practic_class"]["text"], FileID=context.user_data["practic_class"]["file_id"])
    logger.info(f"New submission for exercise {exercise_id} by {user_sql.get_user(student.id).fullname}")
    #TODO: send notification to notification channel of the classroom if it exists

    # notify student that the submission was sent
    if query:
        await query.message.reply_text(
            "Enviado!",
            reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "Enviado!",
            reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
        )
    return ConversationHandler.END
   
async def student_practic_classes_back(update: Update, context: ContextTypes):
    """ Returns to student main menu """
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

    if "practic_class" in context.user_data:
        context.user_data.pop("practic_class")
    
    return ConversationHandler.END


# Handlers

student_practic_classes_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("📓 Clases Prácticas"), student_practic_classes)],
    states={
        states.S_SELECT_PRACTIC_CLASS: [
            CallbackQueryHandler(practic_class_selected, pattern=r"^(practic_class#|new_title_proposal)"),
            paginator_handler,
        ],
        states.S_PRACTIC_CLASS_NEW_TITLE_PROPOSAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_new_title_proposal)],
        states.S_EXERCISE_SELECT: [
            CallbackQueryHandler(practic_class_selected, pattern=r"^new_title_proposal"),   # new title proposal
            CallbackQueryHandler(practic_class_exercise_selected, pattern=r"^exercise#"),
            paginator_handler,
        ],
        states.S_EXERCISE_SEND_SUBMISSION: [CallbackQueryHandler(practic_class_exercise_send_submission, pattern=r"^send_submission")],
        states.S_EXERCISE_SEND_SUBMISSION_DONE: [
            MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, practic_class_exercise_send_submission_done),
            CallbackQueryHandler(practic_class_exercise_send_submission_done, pattern=r"^delete_pending"),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(student_practic_classes_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_student_menu),
    ],
    allow_reentry=True,
)
