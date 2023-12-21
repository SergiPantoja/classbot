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
from sql import user_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, teacher_classroom_sql, token_sql, student_token_sql, guild_sql, activity_type_sql, activity_sql
from bot.teacher_settings import back_to_teacher_menu


async def teacher_activities(update: Update, context: ContextTypes):
    """Teacher activities menu
    Options for creating a new activity type, or viewing existing activities.
    Activity types can be hidden (to hide them from the student menu and pending activities),
    The description and File can be edited.
    Select an activity type to edit it, or to add specific activities if supported.
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
    context.user_data["activity"] = {}

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    # get all activity types (not hidden)
    activity_types = activity_type_sql.get_activity_types(teacher.active_classroom_id)

    if activity_types:
        # Show activity types with pagination.
        # Add buttons for back and create activity type
        buttons = [InlineKeyboardButton(f"{i}. {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"activity_type#{activity_type.id}") for i, activity_type in enumerate(activity_types, start=1)]
        other_buttons = [
            InlineKeyboardButton("Crear actividad", callback_data="create_activity_type"),
        ]
        await update.message.reply_text(
            "Seleccione un tipo de actividad existente o cree uno nuevo",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
        )
        return states.T_ACTIVITIES_CREATE_TYPE
    else:
        await update.message.reply_text(
            "No hay actividades en el aula. Desear crear una?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Crear actividad", callback_data="create_activity_type")]]),
        )
        return states.T_ACTIVITIES_CREATE_TYPE

async def create_activity_type(update: Update, context: ContextTypes):
    """Create a new activity type"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Ingrese el nombre de la actividad",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
    )
    return states.T_ACTIVITIES_TYPE_SEND_NAME
async def activity_type_name(update: Update, context: ContextTypes):
    """Save the activity type name and ask for description"""
    context.user_data["activity"]["type"] = update.message.text

    # if the activity type already exists, and its not hidden, then ask for a new name
    # if the activity type exists and its hidden, then unhide it
    # if the activity type doesn't exist, then create it
    activity_type = activity_type_sql.get_activity_type_by_type(context.user_data["activity"]["type"], teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id)
    activity_token_type = token_type_sql.get_token_type_by_type(context.user_data["activity"]["type"], teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id)
    if activity_type:
        if activity_token_type.hidden:
            token_type_sql.switch_hidden_status(activity_token_type.id)
            await update.message.reply_text(
                f"El tipo de actividad {activity_token_type.type} ya existe, pero está oculto. Se desocultará.",
                reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                f"El tipo de actividad {activity_token_type.type} ya existe. Ingrese un nuevo nombre para el tipo de actividad.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
            )
            return states.T_ACTIVITIES_TYPE_SEND_NAME
    else:
        await update.message.reply_text(
            f'Ingrese una descripción para las actividades de este tipo "{context.user_data["activity"]["type"]}" si desea',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
        )
        return states.T_ACTIVITIES_TYPE_SEND_DESCRIPTION 
async def activity_type_description(update: Update, context: ContextTypes):
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data["activity"]["description"] = None
        await query.edit_message_text(
            "Esta actividad es grupal o individual?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Individual", callback_data="individual")],
                [InlineKeyboardButton("Grupal", callback_data="guild")],
                [InlineKeyboardButton("Atrás", callback_data="back")],
            ])
        )
    else:
        context.user_data["activity"]["description"] = update.message.text
        await update.message.reply_text(
            "Bien! Esta actividad es grupal o individual?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Individual", callback_data="individual")],
                [InlineKeyboardButton("Grupal", callback_data="guild")],
                [InlineKeyboardButton("Atrás", callback_data="back")],
            ])
        )
    return states.T_ACTIVITIES_TYPE_SEND_GUILD_ACTIVITY
async def activity_type_guild(update: Update, context: ContextTypes):
    query = update.callback_query
    await query.answer()
    context.user_data["activity"]["guild_activity"] = (query.data == "guild")
    await query.edit_message_text(
        "Determine si se pueden crear actividades específicas de este tipo.\n"
        "Esto sería similar a los ejercicios de clase práctica, donde un estudiante "
        "puede ganar créditos por cada ejercicio que resuelva, solo una vez.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Si", callback_data="single_submission")],
            [InlineKeyboardButton("No", callback_data="no_single_submission")],
            [InlineKeyboardButton("Atrás", callback_data="back")],
        ])
    )
    return states.T_ACTIVITIES_TYPE_SEND_SINGLE_SUBMISSION
async def activity_type_single_submission(update: Update, context: ContextTypes):
    query = update.callback_query
    await query.answer()
    context.user_data["activity"]["single_submission"] = (query.data == "single_submission")
    await query.edit_message_text(
        "Por último, puede adjuntar un archivo a esta actividad.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")], [InlineKeyboardButton("Cancelar creación", callback_data="back")]])
    )
    return states.T_ACTIVITIES_TYPE_SEND_FILE
async def activity_type_file(update: Update, context: ContextTypes):
    """ Gets the file if sent and creates the activity type """
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
    
    classroom_id = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id
    # create activity type
    activity_type_sql.add_activity_type(
        context.user_data["activity"]["type"],
        classroom_id,
        description=context.user_data["activity"]["description"],
        guild_activity=context.user_data["activity"]["guild_activity"],
        single_submission=context.user_data["activity"]["single_submission"],
        FileID=fid,
    )
    logger.info(f"Activity type {context.user_data['activity']['type']} created by {update.effective_user.id}")

    # Show activity types with pagination.
    # Add buttons for back and create activity type
    activity_types = activity_type_sql.get_activity_types(classroom_id)
    buttons = [InlineKeyboardButton(f"{i}. {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"activity_type#{activity_type.id}") for i, activity_type in enumerate(activity_types, start=1)]
    other_buttons = [
        InlineKeyboardButton("Crear actividad", callback_data="create_activity_type"),
    ]

    if query:
        await query.edit_message_text(
            f'La actividad: "{context.user_data["activity"]["type"]}" ha sido creada!',
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
        )
    else:
        await update.message.reply_text(
            f'La actividad: "{context.user_data["activity"]["type"]}" ha sido creada!',
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
        )
    return states.T_ACTIVITIES_CREATE_TYPE

async def activity_type_selected(update: Update, context: ContextTypes):
    """ Shows the details of the activity_type.
    Allows editing description and FileID, and hiding the activity type.
    If the activity type allows specific activities (single_submission=True), 
    then show them if any exist, and allow creating new ones.
    """
    query = update.callback_query
    await query.answer()

    activity_type_id = int(query.data.split("#")[1])
    activity_type = activity_type_sql.get_activity_type(activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    if activity_type.single_submission:
        text = f"Tipo de actividad: {token_type.type}\n" + f"{'Actividad grupal' if activity_type.guild_activity else 'Actividad individual'}\n"
        if activity_type.description:
            text += f"Descripción: {activity_type.description}\n"
        text += "Este tipo de actividad permite crear actividades específicas. Puede crearlas a continuación o acceder a las existentes.\n"

        activities = activity_sql.get_activities_by_activity_type_id(activity_type_id)
        if activities:
            # Show activities with pagination.
            # Add buttons for back and create activity type
            buttons = [InlineKeyboardButton(f"{i}. {token_sql.get_token(activity.token_id).name}", callback_data=f"activity#{activity.id}") for i, activity in enumerate(activities, start=1)]
            other_buttons = [
                InlineKeyboardButton(f"Crear actividad de {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"create_activity#{activity_type_id}"),
                InlineKeyboardButton("Cambiar descripción" , callback_data="activity_type_change_description"),
                InlineKeyboardButton("Enviar otro archivo", callback_data="activity_type_change_file"),
                InlineKeyboardButton("Ocultar actividad", callback_data="activity_type_hide"),
                InlineKeyboardButton("Atrás", callback_data="back")
            ]
        
            if activity_type.FileID:
                try:
                    try:
                        await query.message.reply_photo(activity_type.FileID, caption=text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
                    except BadRequest:
                        await query.message.reply_document(activity_type.FileID, caption=text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
                except BadRequest:
                    await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar el tipo de actividad para enviar otro archivo.\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
            else:
                await query.edit_message_text(text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
        else:
            if activity_type.FileID:
                try:
                    try:
                        await query.message.reply_photo(activity_type.FileID, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Crear actividad de {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"create_activity#{activity_type_id}")],] + keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
                    except BadRequest:
                        await query.message.reply_document(activity_type.FileID, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Crear actividad de {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"create_activity#{activity_type_id}")],] + keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
                except BadRequest:
                    await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar el tipo de actividad para enviar otro archivo.\n\n" + text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Crear actividad de {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"create_activity#{activity_type_id}")],] + keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
            else:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Crear actividad de {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"create_activity#{activity_type_id}")],] + keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
    else:
        # doesnt support specific activities, only show the details of this activity_type
        # and allow edition and hiding it
        text = f"Actividad: {token_type.type}\n" + f"{'Actividad grupal' if activity_type.guild_activity else 'Actividad individual'}\n"
        if activity_type.description:
            text += f"Descripción: {activity_type.description}\n"
        
        if activity_type.FileID:
            try:    
                try:
                    await query.message.reply_photo(activity_type.FileID, caption=text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
                except BadRequest:
                    await query.message.reply_document(activity_type.FileID, caption=text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
            except BadRequest:
                await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar la actividad para enviar otro archivo.\n\n" + text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
    return states.T_ACTIVITIES_TYPE_INFO




async def teacher_activities_back(update: Update, context: ContextTypes):
    """Go back to teacher menu"""
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

    if "activity" in context.user_data:
        context.user_data.pop("activity")
    return ConversationHandler.END


# Handlers
teacher_activities_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Actividades 📖$"), teacher_activities)],
    states={
        states.T_ACTIVITIES_CREATE_TYPE: [
            CallbackQueryHandler(create_activity_type, pattern=r"^create_activity_type$"),
            CallbackQueryHandler(activity_type_selected, pattern=r"^activity_type#"),
            paginator_handler,
        ],
        states.T_ACTIVITIES_TYPE_SEND_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity_type_name)],
        states.T_ACTIVITIES_TYPE_SEND_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, activity_type_description),
            CallbackQueryHandler(activity_type_description, pattern=r"^continue$"),
            ],
        states.T_ACTIVITIES_TYPE_SEND_GUILD_ACTIVITY: [CallbackQueryHandler(activity_type_guild, pattern=r"^(individual|guild)$")],
        states.T_ACTIVITIES_TYPE_SEND_SINGLE_SUBMISSION: [CallbackQueryHandler(activity_type_single_submission, pattern=r"^(single_submission|no_single_submission)$")],
        states.T_ACTIVITIES_TYPE_SEND_FILE: [
            MessageHandler(filters.Document.ALL | filters.PHOTO, activity_type_file),
            CallbackQueryHandler(activity_type_file, pattern=r"^continue$"),
            ],
        states.T_ACTIVITIES_TYPE_INFO: [
            paginator_handler,
        ]
    },
    fallbacks=[
        CallbackQueryHandler(teacher_activities_back, pattern="back"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
    ],
    allow_reentry=True,
)

