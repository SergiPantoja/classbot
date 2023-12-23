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
        if not exercises[i][0].isalpha() or not exercises[i+1].isdigit():
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
    
    # clean context
    context.user_data.pop("practic_class")

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
    pass

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
            CallbackQueryHandler(practic_class_selected, pattern=r"^activity_type#"),
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
    },
    fallbacks=[
        CallbackQueryHandler(teacher_practic_classes_back, pattern="back"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
    ],
    allow_reentry=True,
)
