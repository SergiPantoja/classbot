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
    # get all practic classes from db (include hidden)
    practic_classes = practic_class_sql.get_practic_classes(teacher.active_classroom_id, include_hidden=True)

    if practic_classes:
        # Show practic classes with pagination
        buttons = [InlineKeyboardButton(f"{i}. {token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class.activity_type_id).token_type_id).type}", callback_data=f"practic_class#{practic_class.id}") for i, practic_class in enumerate(practic_classes, start=1)]
        other_buttons = [InlineKeyboardButton("Crear clase práctica", callback_data="create_practic_class")]
        await update.message.reply_text(
            "Clases prácticas:",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
        )
        return states.T_CP_CREATE
    else:
        await update.message.reply_text(
            "No hay clases prácticas disponibles, desea crear una?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Crear clase práctica", callback_data="create_practic_class")],
                [InlineKeyboardButton("Atrás", callback_data="back")],
            ])
        )
        return states.T_CP_CREATE

async def create_practic_class(update: Update, context: ContextTypes):
    """ Starts the flow to create a practic class.
        First asks for its name (activity_type) followed by each exercise (activity)
        and its value. Then its date, description (optional) and a File (optional).
        Once this is done, the practic class is created with all its exercises.
    """
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Ingrese la Clase Práctica en el formato siguiente:\n\n"
        "<b>Nombre Nombre_del_1er_ejercicio Valor_del_1er_ejercicio Nombre_del_2do_ejercicio Valor_del_2do_ejercicio ...</b>\n\n"
        "Ejemplo:\n"
        "<b>CP1 E1 10000 E2 20000 E3 30000</b>\n\n",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
    )
    return states.T_CP_CREATE_STRING
async def practic_class_string(update: Update, context: ContextTypes):
    """ Receives the practic class string, validates it and asks for the date """
    cp_str = update.message.text
    # get name
    name = cp_str.split()[0]

    # if name exists, ask for another one
    classroom_id = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id
    practic_class = practic_class_sql.get_practic_class_by_name(name, classroom_id)
    if practic_class:
        await update.message.reply_text(
            "Ya existe una clase práctica con ese nombre, por favor ingrese otro nombre",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
        return states.T_CP_CREATE_STRING
    
    # get exercises and values, validate them 
    # must be even, first member of each pair must start with a letter, second must be a positive int
    exercises = cp_str.split()[1:]
    if len(exercises) % 2 != 0:
        await update.message.reply_text(
            "El formato de la clase práctica es incorrecto, por favor intente de nuevo",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
        return states.T_CP_CREATE_STRING
    for i in range(0, len(exercises), 2):
        if not exercises[i+1].isdigit():
            await update.message.reply_text(
                "El formato de la clase práctica es incorrecto, por favor intente de nuevo",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
            )
            return states.T_CP_CREATE_STRING
    
    # save exercises and values in context
    context.user_data["practic_class"]["exercises"] = exercises
    context.user_data["practic_class"]["name"] = name

    await update.message.reply_text(
        "Inserte la fecha de la clase práctica en este formato: dd-mm-aaaa",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
    )
    return states.T_CP_CREATE_DATE
async def practic_class_date(update: Update, context: ContextTypes):
    """ Receives the practic class date, validates it and asks for the description """
    date_str = update.message.text
    # validate date
    try:
        date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        await update.message.reply_text(
            "El formato de la fecha es incorrecto, por favor intente de nuevo",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
        return states.T_CP_CREATE_DATE
    
    # save date in context
    context.user_data["practic_class"]["date"] = date

    await update.message.reply_text(
        "Inserte la descripción de la clase práctica o presione continuar.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
    )
    return states.T_CP_CREATE_DESCRIPTION
async def practic_class_description(update: Update, context: ContextTypes):
    """ Receives the description if sent and asks for a file"""
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data["practic_class"]["description"] = None
        await query.edit_message_text(
            "Por último, puede adjuntar un archivo a la clase práctica si lo desea.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
        )
        return states.T_CP_CREATE_FILE
    else:
        description = update.message.text
        context.user_data["practic_class"]["description"] = description
        await update.message.reply_text(
            "Por último, puede adjuntar un archivo a la clase práctica si lo desea.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
        )
        return states.T_CP_CREATE_FILE
async def practic_class_file(update: Update, context: ContextTypes):
    """ Receives the file if sent and creates the practic class and its exercises"""
    query = update.callback_query
    if query:
        await query.answer()
        file = None
    else:
        file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id

    # get classroom id
    classroom_id = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id

    # create practic class
    practic_class_sql.add_practic_class(
        date = context.user_data["practic_class"]["date"],
        name = context.user_data["practic_class"]["name"],
        classroom_id = classroom_id,
        description = context.user_data["practic_class"]["description"],
        FileID = fid,
    )
    logger.info(f"Created practic class {context.user_data['practic_class']['name']}")

    # create exercises
    practic_class_id = practic_class_sql.get_practic_class_by_name(context.user_data["practic_class"]["name"], classroom_id).id
    exercises = context.user_data["practic_class"]["exercises"]
    for i in range(0, len(exercises), 2):
        practic_class_exercises_sql.add_practic_class_exercise(
            value=int(exercises[i+1]),
            practic_class_id=practic_class_id,
            classroom_id=classroom_id,
            name=exercises[i],
        )
        logger.info(f"Created practic class exercise {exercises[i]}")
    
    # show practic classes with pagination
    practic_classes = practic_class_sql.get_practic_classes(classroom_id=classroom_id, include_hidden=True)
    buttons = [InlineKeyboardButton(f"{i}. {token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class.activity_type_id).token_type_id).type}", callback_data=f"practic_class#{practic_class.id}") for i, practic_class in enumerate(practic_classes, start=1)]
    other_buttons = [InlineKeyboardButton("Crear clase práctica", callback_data="create_practic_class")]
    
    if query:
        await query.edit_message_text(
        "Clases prácticas:",
        reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
    )
    else:
        await update.message.reply_text(
            "Clases prácticas:",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
        )
    return states.T_CP_CREATE

async def practic_class_selected(update: Update, context: ContextTypes):
    """ Shows the details of the selected practic class.
        Allows editing the date, the description and FileID. Also deleting the practic class.
        Shows the exercises with pagination and allows creating new ones.
    """
    query = update.callback_query
    await query.answer()

    practic_class_id = int(query.data.split("#")[1])
    # save practic class id in context
    context.user_data["practic_class"]["practic_class_id"] = practic_class_id

    practic_class = practic_class_sql.get_practic_class(practic_class_id)
    activity_type = activity_type_sql.get_activity_type(practic_class.activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    text = f"<b>Clase práctica:</b> {token_type.type}\n"
    text += f"<b>Fecha:</b> {practic_class.date.strftime('%d-%m-%Y')}\n"
    if activity_type.description:
        text += f"<b>Descripción:</b> {activity_type.description}\n"
    text += "<b>Ejercicios:</b>\n"

    exercises = practic_class_exercises_sql.get_practic_class_exercises_by_practic_class_id(practic_class_id)
    if exercises:
        # sort exercises by name
        exercises.sort(key=lambda x: token_sql.get_token(activity_sql.get_activity(x.activity_id).token_id).name)
        buttons = [InlineKeyboardButton(f"{i}. {token_sql.get_token(activity_sql.get_activity(exercise.activity_id).token_id).name} - ({exercise.value})", callback_data=f"exercise#{exercise.id}") for i, exercise in enumerate(exercises, start=1)]    
        other_buttons = [
            InlineKeyboardButton("Crear ejercicio", callback_data=f"create_exercise#{practic_class_id}"),
            InlineKeyboardButton("Cambiar fecha", callback_data="practic_class_change_date"),
            InlineKeyboardButton("Cambiar descripción", callback_data="practic_class_change_description"),
            InlineKeyboardButton("Enviar otro archivo", callback_data="practic_class_change_file"),
            InlineKeyboardButton("Eliminar clase práctica", callback_data="practic_class_delete"),
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
    else:
        if activity_type.FileID:
            try:
                try:
                    await query.message.reply_photo(activity_type.FileID, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Crear ejercicio", callback_data=f"create_exercise#{practic_class_id}")],] + keyboards.TEACHER_PRACTIC_CLASS_OPTIONS))
                except BadRequest:
                    await query.message.reply_document(activity_type.FileID, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Crear ejercicio", callback_data=f"create_exercise#{practic_class_id}")],] + keyboards.TEACHER_PRACTIC_CLASS_OPTIONS))
            except BadRequest:
                await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar la clase práctica para enviar otro archivo.\n\n" + text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Crear ejercicio", callback_data=f"create_exercise#{practic_class_id}")],] + keyboards.TEACHER_PRACTIC_CLASS_OPTIONS))
        else:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Crear ejercicio", callback_data=f"create_exercise#{practic_class_id}")],] + keyboards.TEACHER_PRACTIC_CLASS_OPTIONS))
    return states.T_CP_INFO
async def practic_class_edit_date(update: Update, context: ContextTypes):
    """ Asks for the new date"""
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            query.message.caption + "\n\n"
            "Inserte la nueva fecha de la clase práctica en este formato: dd-mm-aaaa",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
    else:
        await query.edit_message_text(
            "Inserte la nueva fecha de la clase práctica en este formato: dd-mm-aaaa",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_CP_EDIT_DATE
async def practic_class_edit_date_done(update: Update, context: ContextTypes):
    """ Updates the practic class with the new date """
    date_str = update.message.text
    # validate date
    try:
        date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        await update.message.reply_text(
            "El formato de la fecha es incorrecto, por favor intente de nuevo",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
        return states.T_CP_EDIT_DATE
    
    practic_class_id = context.user_data["practic_class"]["practic_class_id"]
    practic_class_sql.update_date(practic_class_id, date)
    logger.info(f"Updated practic class date to {date}")
    await update.message.reply_text(
        "fecha actualizada",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END
async def practic_class_edit_description(update: Update, context: ContextTypes):
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            query.message.caption + "\n\n"
            "Inserte la nueva descripción de la clase práctica.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Inserte la nueva descripción de la clase práctica.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_CP_EDIT_DESCRIPTION
async def practic_class_edit_description_done(update: Update, context: ContextTypes):
    """ Updates the practic class with the new description """
    description = update.message.text
    practic_class_id = context.user_data["practic_class"]["practic_class_id"]
    practic_class_sql.update_description(practic_class_id, description)
    logger.info(f"Updated practic class description to {description}")
    await update.message.reply_text(
        "Descripción actualizada",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END
async def practic_class_edit_file(update: Update, context: ContextTypes):
    """ Asks for the new file """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            query.message.caption + "\n\n"
            "Inserte el nuevo archivo de la clase práctica.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Inserte el nuevo archivo de la clase práctica.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_CP_EDIT_FILE
async def practic_class_edit_file_done(update: Update, context: ContextTypes):
    practic_class_id = context.user_data["practic_class"]["practic_class_id"]
    file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id
    practic_class_sql.update_file(practic_class_id, fid)
    logger.info(f"Updated practic class file to {fid}")
    await update.message.reply_text(
        "Archivo actualizado",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END
async def practic_class_delete(update: Update, context: ContextTypes):
    """ Asks for confirmation to delete the practic class """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            query.message.caption + "\n\n"
            "Está seguro que desea eliminar esta clase práctica? Esta acción no se puede deshacer.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="practic_class_delete_confirm"), InlineKeyboardButton("No", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Está seguro que desea eliminar esta clase práctica? Esta acción no se puede deshacer.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="practic_class_delete_confirm"), InlineKeyboardButton("No", callback_data="back")]])
        )
    return states.T_CP_DELETE
async def practic_class_delete_confirm(update: Update, context: ContextTypes):
    """ Deletes the practic class 
        Deletes the token_type of the activity_type of the practic class and
        should delete the activity_type -> practic_class and token -> activity
        -> practic_class_exercise in cascade.
    """
    query = update.callback_query
    await query.answer()

    practic_class_id = context.user_data["practic_class"]["practic_class_id"]
    token_type_id = activity_type_sql.get_activity_type(practic_class_sql.get_practic_class(practic_class_id).activity_type_id).token_type_id
    token_type_sql.delete_token_type(token_type_id)
    logger.info(f"Deleted token_type {token_type_id}")
    await query.message.reply_text(
        "Clase práctica eliminada",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

async def create_exercise(update: Update, context: ContextTypes):
    """ Starts the flow to create a practic_class_exercise  
        Asks for name, then value, optional description and FileID.
        Finally asks if partial credtis is allowed, which means the teacher
        can later approve the pending of this exercise (or manually review it)
        and assing any amount of credits between 0 and the max value instead of
        just 0 or the max value.
    """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            query.message.caption + "\n\n"
            "Ingrese el nombre del ejercicio.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Ingrese el nombre del ejercicio.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_CP_CREATE_EXERCISE_NAME
async def practic_class_exercise_name(update: Update, context: ContextTypes):
    """ Receives the exercise name and asks for the value """
    name = update.message.text
    # save in context
    context.user_data["practic_class"]["exercise_name"] = name
    await update.message.reply_text(
        "Ingrese el valor del ejercicio.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
    )
    return states.T_CP_CREATE_EXERCISE_VALUE
async def practic_class_exercise_value(update: Update, context: ContextTypes):
    """ Receives the value, validates is the correct type and asks for the description """
    value = update.message.text
    # validate value
    if not value.isdigit():
        await update.message.reply_text(
            "El formato del valor es incorrecto, por favor intente de nuevo",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
        return states.T_CP_CREATE_EXERCISE_VALUE
    # save in context
    context.user_data["practic_class"]["exercise_value"] = value
    await update.message.reply_text(
        "Ingrese la descripción del ejercicio o presione continuar.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
    )
    return states.T_CP_CREATE_EXERCISE_DESCRIPTION
async def practic_class_exercise_description(update: Update, context: ContextTypes):
    """ Receives the description if sent and asks for the file """
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data["practic_class"]["exercise_description"] = None
        await query.edit_message_text(
            "Puede adjuntar un archivo al ejercicio si lo desea.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
        )
    else:
        description = update.message.text
        context.user_data["practic_class"]["exercise_description"] = description
        await update.message.reply_text(
            "Puede adjuntar un archivo al ejercicio si lo desea.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
        )
    return states.T_CP_CREATE_EXERCISE_FILE
async def practic_class_exercise_file(update: Update, context: ContextTypes):
    """ Receives the file if sent and asks if partial credits are allowed """
    query = update.callback_query
    if query:
        await query.answer()
        file = None
    else:
        file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id
    
    # save in context
    context.user_data["practic_class"]["exercise_file_id"] = fid

    if query:
        await query.edit_message_text(
            "Permitir créditos parciales?\n\nEsto significa que si el estudiante envia una ejercicio parcialmente completo/correcto, el profesor puede aprobar la tarea y asignarle una cantidad de créditos entre 0 y el valor máximo del ejercicio.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")]])
        )
    else:
        await update.message.reply_text(
            "Permitir créditos parciales?\n\nEsto significa que si el estudiante envia una ejercicio parcialmente completo/correcto, el profesor puede aprobar la tarea y asignarle una cantidad de créditos entre 0 y el valor máximo del ejercicio.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")]])
        )
    return states.T_CP_CREATE_EXERCISE_PARTIAL_CREDITS
async def practic_class_exercise_partial_credits(update: Update, context: ContextTypes):
    """ Receives the partial credits option and creates the exercise """
    query = update.callback_query
    await query.answer()

    partial_credits = query.data == "yes"

    # get classroom id
    classroom_id = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id
    practic_class_id = context.user_data["practic_class"]["practic_class_id"]

    # create exercise
    practic_class_exercises_sql.add_practic_class_exercise(
        value=int(context.user_data["practic_class"]["exercise_value"]),
        practic_class_id=practic_class_id,
        classroom_id=classroom_id,
        name=context.user_data["practic_class"]["exercise_name"],
        partial_credits_allowed=partial_credits,
        description=context.user_data["practic_class"]["exercise_description"],
        FileID=context.user_data["practic_class"]["exercise_file_id"],
    )
    logger.info(f"Created practic class exercise {context.user_data['practic_class']['exercise_name']}")

    # show practic class exercises with pagination
    practic_class = practic_class_sql.get_practic_class(practic_class_id)
    activity_type = activity_type_sql.get_activity_type(practic_class.activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    text = f"<b>Clase práctica:</b> {token_type.type}\n"
    text += f"<b>Fecha:</b> {practic_class.date.strftime('%d-%m-%Y')}\n"
    if activity_type.description:
        text += f"<b>Descripción:</b> {activity_type.description}\n"
    text += "<b>Ejercicios:</b>\n"

    exercises = practic_class_exercises_sql.get_practic_class_exercises_by_practic_class_id(practic_class_id)
    # sort exercises by name
    exercises.sort(key=lambda x: token_sql.get_token(activity_sql.get_activity(x.activity_id).token_id).name)
    buttons = [InlineKeyboardButton(f"{i}. {token_sql.get_token(activity_sql.get_activity(exercise.activity_id).token_id).name} - ({exercise.value})", callback_data=f"exercise#{exercise.id}") for i, exercise in enumerate(exercises, start=1)]
    other_buttons = [
        InlineKeyboardButton("Crear ejercicio", callback_data=f"create_exercise#{practic_class_id}"),
        InlineKeyboardButton("Cambiar fecha", callback_data="practic_class_change_date"),
        InlineKeyboardButton("Cambiar descripción", callback_data="practic_class_change_description"),
        InlineKeyboardButton("Enviar otro archivo", callback_data="practic_class_change_file"),
        InlineKeyboardButton("Eliminar clase práctica", callback_data="practic_class_delete"),
    ]
    if query:
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
    else:
        if activity_type.FileID:
            try:
                try:
                    await update.message.reply_photo(activity_type.FileID, caption=text, parse_mode="HTML", reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
                except BadRequest:
                    await update.message.reply_document(activity_type.FileID, caption=text, parse_mode="HTML", reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
            except BadRequest:
                await update.message.reply_text("Se ha producido un error al enviar el archivo. Puede intentar editar la clase práctica para enviar otro archivo.\n\n" + text, parse_mode="HTML", reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
    return states.T_CP_INFO

async def exercise_selected(update: Update, context: ContextTypes):
    """ Shows the details of the selected practic class exercise.
        Doesnt allow edition for now.
        Show options for deleting it or manually reviewing it.
    """
    query = update.callback_query
    await query.answer()

    exercise_id = int(query.data.split("#")[1])
    # save exercise id in context
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
                await query.message.reply_photo(activity.FileID, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PRACTIC_CLASS_EXERCISE_OPTIONS))
            except BadRequest:
                await query.message.reply_document(activity.FileID, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PRACTIC_CLASS_EXERCISE_OPTIONS))
        except BadRequest:
            await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar el ejercicio para enviar otro archivo.\n\n" + text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PRACTIC_CLASS_EXERCISE_OPTIONS))
    else:
        if query.message.caption:
            await query.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PRACTIC_CLASS_EXERCISE_OPTIONS))
        else:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PRACTIC_CLASS_EXERCISE_OPTIONS))
    return states.T_CP_EXERCISE_INFO
async def practic_class_exercise_delete(update: Update, context: ContextTypes):
    """ Ask for confirmation to delete the exercise """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            query.message.caption + "\n\n"
            "Está seguro que desea eliminar este ejercicio? Esta acción no se puede deshacer.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="practic_class_exercise_delete_confirm"), InlineKeyboardButton("No", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Está seguro que desea eliminar este ejercicio? Esta acción no se puede deshacer.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="practic_class_exercise_delete_confirm"), InlineKeyboardButton("No", callback_data="back")]])
        )
    return states.T_CP_EXERCISE_DELETE
async def practic_class_exercise_delete_confirm(update: Update, context: ContextTypes):
    """ Deletes the practic class exercise.
        Deletes the token of the activity of the exercise and
        should delete the activity -> practic_class_exercise in cascade.
    """
    query = update.callback_query
    await query.answer()

    exercise_id = context.user_data["practic_class"]["exercise_id"]
    token_id = activity_sql.get_activity(practic_class_exercises_sql.get_practic_class_exercise(exercise_id).activity_id).token_id
    token_sql.delete_token(token_id)
    logger.info(f"Deleted token {token_id}")
    await query.message.reply_text(
        "Ejercicio eliminado",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

async def practic_class_exercise_review(update: Update, context: ContextTypes):
    """ Here teachers manually give credits to students for an exercise of a practic class"""
    query = update.callback_query
    await query.answer()

    # get exercise
    exercise = practic_class_exercises_sql.get_practic_class_exercise(context.user_data["practic_class"]["exercise_id"])
    activity = activity_sql.get_activity(exercise.activity_id)
    token = token_sql.get_token(activity.token_id)

    # get students that dont have a grade for this exercise yet
    students = student_sql.get_students_by_classroom(token.classroom_id)
    students = [student for student in students if not student_token_sql.exists(student.id, token.id)]
    if not students:
        if query.message.caption:
            await query.edit_message_caption(
                query.message.caption + "\n\n"
                "Todos los estudiantes ya tienen una nota para este ejercicio.",
                reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PRACTIC_CLASS_EXERCISE_OPTIONS)
            )
        else:
            await query.edit_message_text(
                "Todos los estudiantes ya tienen una nota para este ejercicio.",
                reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PRACTIC_CLASS_EXERCISE_OPTIONS)
            )
        return states.T_CP_EXERCISE_INFO
    buttons = [InlineKeyboardButton(f"{i}. {user_sql.get_user(student.id).fullname}", callback_data=f"student#{student.id}") for i, student in enumerate(students, start=1)]
    text = "Seleccione al estudiante"

    if query.message.caption:
        await query.edit_message_caption(
            text,
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True)
        )
    else:
        await query.edit_message_text(
            text,
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True)
        )
    return states.T_CP_EXERCISE_REVIEW
async def review_exercise_select_student(update: Update, context: ContextTypes):
    """ Saves the student id. 
        Then checks if the exercise allows partial credits, if it does, asks 
        for the credits amount (optional but if sent must be between 0 and the
        exercise max value). If it doesnt allow partial credits, goes to the next
        check.
        Then checks if the practic class date is in the past, if it is, asks if 
        the student sent the exercise before the practic class date (for cases
        where the teacher didnt have time to review it yet). If it isnt,
        it means the student sent the exercise before the date.
        Finally, if none of the previous checks apply, it approves the exercise,
        assigns the credits and sends a message to the student.
    """
    query = update.callback_query
    await query.answer()

    student_id = int(query.data.split("#")[1])
    # save student id in context
    context.user_data["practic_class"]["student_id"] = student_id

    # get exercise and practic class
    exercise = practic_class_exercises_sql.get_practic_class_exercise(context.user_data["practic_class"]["exercise_id"])
    practic_class = practic_class_sql.get_practic_class(exercise.practic_class_id)

    # check if exercise allows partial credits
    if exercise.partial_credits_allowed:
        if query.message.caption:
            await query.edit_message_caption(
                "Ingrese la cantidad de créditos entre 0 y el valor máximo del ejercicio.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
            )
        else:
            await query.edit_message_text(
                "Ingrese la cantidad de créditos entre 0 y el valor máximo del ejercicio.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
            )
        return states.T_CP_EXERCISE_REVIEW_PARTIAL_CREDITS
    else:    
        # check if practic class date is in the past
        if practic_class.date < datetime.datetime.now():
            # ask if student sent the exercise before the practic class date
            if query.message.caption:
                await query.edit_message_caption(
                    "El estudiante envió el ejercicio antes de la fecha de la clase práctica?",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")]])
                )
            else:
                await query.edit_message_text(
                    "El estudiante envió el ejercicio antes de la fecha de la clase práctica?",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")]])
                )
            return states.T_CP_EXERCISE_REVIEW_DATE
        else:
            # No partial credits and date is in the future, assing max value x2 (bonus for sending it early)
            student = student_sql.get_student(student_id)
            token = token_sql.get_token(activity_sql.get_activity(exercise.activity_id).token_id)
            teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
            student_token_sql.add_student_token(student.id, token.id, exercise.value * 2, teacher_id=teacher.id)
            logger.info(f"Added {exercise.value * 2} credits to student {student.id} for exercise {token.name}")
            # Create approved pending
            token_type = token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class_sql.get_practic_class(exercise.practic_class_id).activity_type_id).token_type_id)
            text = f"Créditos otorgados manualmente por el profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} al estudiantes {user_sql.get_user(student.id).fullname} por el ejercicio {token.name} de la clase práctica {token_type.type}"
            pending_sql.add_pending(student_id=student.id, classroom_id=teacher.active_classroom_id, token_type_id=token_type.id, token_id=token.id, status="APPROVED", approved_by=teacher.id, text=text)
            # notify student
            text = f"El profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} le ha otorgado {exercise.value * 2} créditos por el ejercicio {token.name} de la clase práctica {token_type.type}"
            try:
                await context.bot.send_message(
                    chat_id=user_sql.get_user(student.id).telegram_chatid,
                    text=text,
                )
            except BadRequest:
                logger.error(f"Error sending message to student {user_sql.get_user(student.id).fullname} (chat_id: {user_sql.get_user(student.id).telegram_chatid})")
            await query.message.reply_text(
                "Créditos otorgados!",
                reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
            )
            return ConversationHandler.END
async def review_partial_credits(update: Update, context: ContextTypes):
    """ Receives partial credits amount and validates it.
        Then check date and either approves the exercise or asks if the student
        sent the exercise before the date.
    """
    partial_value = update.message.text
    # validate value
    if not partial_value.isdigit():
        await update.message.reply_text(
            "El formato del valor es incorrecto, por favor intente de nuevo",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
        return states.T_CP_EXERCISE_REVIEW_PARTIAL_CREDITS
    # get exercise and practic class
    exercise = practic_class_exercises_sql.get_practic_class_exercise(context.user_data["practic_class"]["exercise_id"])
    practic_class = practic_class_sql.get_practic_class(exercise.practic_class_id)
    # check if value is between 0 and max value
    if int(partial_value) < 0 or int(partial_value) > exercise.value:
        await update.message.reply_text(
            f"El valor debe estar entre 0 y el valor del ejercicio: {exercise.value}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
        return states.T_CP_EXERCISE_REVIEW_PARTIAL_CREDITS
    
    # check if practic class date is in the past
    if practic_class.date < datetime.datetime.now():
        # save partial value in context
        context.user_data["practic_class"]["partial_value"] = partial_value
        # ask if student sent the exercise before the practic class date
        await update.message.reply_text(
            "El estudiante envió el ejercicio antes de la fecha de la clase práctica?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Si", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")]])
        )
        return states.T_CP_EXERCISE_REVIEW_DATE
    else:
        # Partial credits and date is in the future, assing partial value x2 (bonus for sending it early)
        student = student_sql.get_student(context.user_data["practic_class"]["student_id"])
        token = token_sql.get_token(activity_sql.get_activity(exercise.activity_id).token_id)
        teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
        student_token_sql.add_student_token(student.id, token.id, int(partial_value) * 2, teacher_id=teacher.id)
        logger.info(f"Added {int(partial_value) * 2} credits to student {student.id} for exercise {token.name}")
        # Create approved pending
        token_type = token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class_sql.get_practic_class(exercise.practic_class_id).activity_type_id).token_type_id)
        text = f"Créditos otorgados manualmente por el profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} al estudiantes {user_sql.get_user(student.id).fullname} por el ejercicio {token.name} de la clase práctica {token_type.type}"
        pending_sql.add_pending(student_id=student.id, classroom_id=teacher.active_classroom_id, token_type_id=token_type.id, token_id=token.id, status="APPROVED", approved_by=teacher.id, text=text)
        # notify student
        text = f"El profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} le ha otorgado {int(partial_value) * 2} créditos por el ejercicio {token.name} de la clase práctica {token_type.type}"
        try:
            await context.bot.send_message(
                chat_id=user_sql.get_user(student.id).telegram_chatid,
                text=text,
            )
        except BadRequest:
            logger.error(f"Error sending message to student {user_sql.get_user(student.id).fullname} (chat_id: {user_sql.get_user(student.id).telegram_chatid})")
        await update.message.reply_text(
            "Créditos otorgados!",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
        return ConversationHandler.END
async def review_exercise_date(update: Update, context: ContextTypes):
    """ If the student sent the exercise before the date, assing double the credits.
        If not, assing just the value, where value is the partial credits amount
        if 'partial_value' is in context, else is the max value.
    """
    query = update.callback_query
    await query.answer()

    sent_before_date = query.data == "yes"
    # get exercise
    exercise = practic_class_exercises_sql.get_practic_class_exercise(context.user_data["practic_class"]["exercise_id"])
    # get value
    if "partial_value" in context.user_data["practic_class"]:
        value = int(context.user_data["practic_class"]["partial_value"])
    else:
        value = exercise.value
    if sent_before_date:
        value *= 2
    
    # assing credits
    student = student_sql.get_student(context.user_data["practic_class"]["student_id"])
    token = token_sql.get_token(activity_sql.get_activity(exercise.activity_id).token_id)
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    student_token_sql.add_student_token(student.id, token.id, value, teacher_id=teacher.id)
    logger.info(f"Added {value} credits to student {student.id} for exercise {token.name}")
    # Create approved pending
    token_type = token_type_sql.get_token_type(activity_type_sql.get_activity_type(practic_class_sql.get_practic_class(exercise.practic_class_id).activity_type_id).token_type_id)
    text = f"Créditos otorgados manualmente por el profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} al estudiantes {user_sql.get_user(student.id).fullname} por el ejercicio {token.name} de la clase práctica {token_type.type}"
    pending_sql.add_pending(student_id=student.id, classroom_id=teacher.active_classroom_id, token_type_id=token_type.id, token_id=token.id, status="APPROVED", approved_by=teacher.id, text=text)
    # notify student
    text = f"El profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} le ha otorgado {value} créditos por el ejercicio {token.name} de la clase práctica {token_type.type}"
    try:
        await context.bot.send_message(
            chat_id=user_sql.get_user(student.id).telegram_chatid,
            text=text,
        )
    except BadRequest:
        logger.error(f"Error sending message to student {user_sql.get_user(student.id).fullname} (chat_id: {user_sql.get_user(student.id).telegram_chatid})")
    await query.message.reply_text(
        "Créditos otorgados!",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

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
        states.T_CP_CREATE: [
            CallbackQueryHandler(create_practic_class, pattern="create_practic_class"),
            CallbackQueryHandler(practic_class_selected, pattern=r"^practic_class#"),
            paginator_handler,
        ],
        states.T_CP_CREATE_STRING: [MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_string)],
        states.T_CP_CREATE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_date)],
        states.T_CP_CREATE_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_description),
            CallbackQueryHandler(practic_class_description, pattern=r"^continue$"),
            ],
        states.T_CP_CREATE_FILE: [
            MessageHandler(filters.Document.ALL | filters.PHOTO, practic_class_file),
            CallbackQueryHandler(practic_class_file, pattern=r"^continue$"),
            ],

        states.T_CP_INFO: [
            CallbackQueryHandler(exercise_selected, pattern=r"^exercise#"),
            paginator_handler,
            CallbackQueryHandler(practic_class_edit_date, pattern=r"^practic_class_change_date$"),
            CallbackQueryHandler(practic_class_edit_description, pattern=r"^practic_class_change_description$"),
            CallbackQueryHandler(practic_class_edit_file, pattern=r"^practic_class_change_file$"),
            CallbackQueryHandler(practic_class_delete, pattern=r"^practic_class_delete$"),
            CallbackQueryHandler(create_exercise, pattern=r"^create_exercise#"),
        ],
        states.T_CP_EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_edit_date_done)],
        states.T_CP_EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_edit_description_done)],
        states.T_CP_EDIT_FILE: [MessageHandler(filters.Document.ALL | filters.PHOTO, practic_class_edit_file_done)],
        states.T_CP_DELETE: [CallbackQueryHandler(practic_class_delete_confirm, pattern=r"^practic_class_delete_confirm$")],

        states.T_CP_CREATE_EXERCISE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_exercise_name)],
        states.T_CP_CREATE_EXERCISE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_exercise_value)],
        states.T_CP_CREATE_EXERCISE_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, practic_class_exercise_description),
            CallbackQueryHandler(practic_class_exercise_description, pattern=r"^continue$"),
            ],
        states.T_CP_CREATE_EXERCISE_FILE: [
            MessageHandler(filters.Document.ALL | filters.PHOTO, practic_class_exercise_file),
            CallbackQueryHandler(practic_class_exercise_file, pattern=r"^continue$"),
            ],
        states.T_CP_CREATE_EXERCISE_PARTIAL_CREDITS: [CallbackQueryHandler(practic_class_exercise_partial_credits, pattern=r"^(yes|no$)")],
        
        states.T_CP_EXERCISE_INFO: [
            CallbackQueryHandler(practic_class_exercise_delete, pattern=r"^practic_class_exercise_delete$"),
            CallbackQueryHandler(practic_class_exercise_review, pattern=r"^practic_class_exercise_review$"),
        ],
        states.T_CP_EXERCISE_DELETE: [CallbackQueryHandler(practic_class_exercise_delete_confirm, pattern=r"^practic_class_exercise_delete_confirm$")],

        states.T_CP_EXERCISE_REVIEW: [
            CallbackQueryHandler(review_exercise_select_student, pattern=r"^student#"),
            paginator_handler,
        ],
        states.T_CP_EXERCISE_REVIEW_PARTIAL_CREDITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_partial_credits)],
        states.T_CP_EXERCISE_REVIEW_DATE: [CallbackQueryHandler(review_exercise_date, pattern=r"^(yes|no$)")],
    },
    fallbacks=[
        CallbackQueryHandler(teacher_practic_classes_back, pattern="back"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
    ],
    allow_reentry=True,
)
