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
            activity_type_sql.unhide_activity_type(activity_type.id)
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
    # Save activity_type id in context
    context.user_data['activity']['activity_type_id'] = activity_type_id

    activity_type = activity_type_sql.get_activity_type(activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    if activity_type.single_submission:
        text = f"Tipo de actividad: {token_type.type}\n" + f"{'Actividad grupal' if activity_type.guild_activity else 'Actividad individual'}\n"
        if activity_type.description:
            text += f"Descripción: {activity_type.description}\n"
        text += "\nEste tipo de actividad permite crear actividades específicas. Puede crearlas a continuación o acceder a las existentes.\n"

        activities = activity_sql.get_activities_by_activity_type_id(activity_type_id)
        if activities:
            # Show activities with pagination.
            # Add buttons for back and create activity type
            buttons = [InlineKeyboardButton(f"{i}. {token_sql.get_token(activity.token_id).name}", callback_data=f"activity#{activity.id}") for i, activity in enumerate(activities, start=1)]
            other_buttons = [
                InlineKeyboardButton(f"Crear actividad", callback_data=f"create_activity#{activity_type_id}"),
                InlineKeyboardButton("Cambiar descripción" , callback_data="activity_type_change_description"),
                InlineKeyboardButton("Enviar otro archivo", callback_data="activity_type_change_file"),
                InlineKeyboardButton("Ocultar actividad", callback_data="activity_type_hide"),
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
                        await query.message.reply_photo(activity_type.FileID, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Crear actividad", callback_data=f"create_activity#{activity_type_id}")],] + keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
                    except BadRequest:
                        await query.message.reply_document(activity_type.FileID, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Crear actividad", callback_data=f"create_activity#{activity_type_id}")],] + keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
                except BadRequest:
                    await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar el tipo de actividad para enviar otro archivo.\n\n" + text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Crear actividad", callback_data=f"create_activity#{activity_type_id}")],] + keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
            else:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Crear actividad")],] + keyboards.TEACHER_ACTIVITY_TYPE_OPTIONS))
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
async def activity_type_edit_description(update: Update, context: ContextTypes):
    """ Asks the user for a new description """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            "Ingrese una nueva descripción para esta actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Ingrese una nueva descripción para esta actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_ACTIVITIES_TYPE_EDIT_DESCRIPTION
async def activity_type_edit_description_done(update: Update, context: ContextTypes):
    """ Updates the activity_type with the new description """
    activity_type_id = context.user_data['activity']['activity_type_id']
    new_description = update.message.text
    activity_type_sql.update_description(activity_type_id, new_description)
    logger.info(f"Activity type {activity_type_id} description updated by {update.effective_user.id}")
    await update.message.reply_text(
        "Descripción actualizada!",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END
async def activity_type_edit_file(update: Update, context: ContextTypes):
    """ Asks the user to send a new file """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            "Envíe un nuevo archivo para esta actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Envíe un nuevo archivo para esta actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_ACTIVITIES_TYPE_EDIT_FILE
async def activity_type_edit_file_done(update: Update, context: ContextTypes):
    """ Updates the activity_type with the new file id """
    activity_type_id = context.user_data['activity']['activity_type_id']
    file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id
    activity_type_sql.update_file(activity_type_id, fid)
    logger.info(f"Activity type {activity_type_id} file updated by {update.effective_user.id}")
    await update.message.reply_text(
        "Archivo actualizado!",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END
async def activity_type_hide(update: Update, context: ContextTypes):
    """ Switch the hidden value of the token_type associated with this activity.
    Should be always False, since there is no flow to arrive here if it is True.
    """
    query = update.callback_query
    await query.answer()

    activity_type_id = context.user_data['activity']['activity_type_id']
    activity_type_sql.hide_activity_type(activity_type_id)
    logger.info(f"Activity type {activity_type_id} hidden by {update.effective_user.id}: {token_type_sql.get_token_type(activity_type_sql.get_activity_type(activity_type_id).token_type_id).hidden}")
    
    await query.message.reply_text(
        "Actividad oculta!\n Si desea volver a mostrarla deberá crear una nueva actividad con el mismo nombre.",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

async def create_activity(update: Update, context: ContextTypes):
    """ Starts the flow to create a subactivity, asks for name """
    query = update.callback_query
    await query.answer()

    activity_type_id = int(query.data.split("#")[1])
    # Save activity_type id in context
    context.user_data['activity']['activity_type_id'] = activity_type_id
    
    if query.message.caption:
        await query.edit_message_caption(
            "Ingrese el nombre de la actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Ingrese el nombre de la actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_ACTIVITY_SEND_NAME
async def activity_name(update: Update, context: ContextTypes):
    """ Saves the name of the activity and asks for description """
    context.user_data['activity']['type'] = update.message.text

    await update.message.reply_text(
        "Ingrese una descripción para esta actividad si lo desea",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
    )
    return states.T_ACTIVITY_SEND_DESCRIPTION
async def activity_description(update: Update, context: ContextTypes):
    """ Saves the description of the activity and asks for file """
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data["activity"]["description"] = None
        await query.edit_message_text(
            "Adjunte un archivo a esta actividad si lo desea",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
        )
    else:
        context.user_data["activity"]["description"] = update.message.text
        await update.message.reply_text(
            "Adjunte un archivo a esta actividad si lo desea",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue")]])
        )
    return states.T_ACTIVITY_SEND_FILE
async def activity_file(update: Update, context: ContextTypes):
    """ Saves the fileID of the activity and asks for deadline """
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
    
    context.user_data["activity"]["FileID"] = fid

    if query:
        await query.edit_message_text(
            "Puede ingresar una fecha límite de entrega para esta actividad, o presionar continuar para finalizar la creación.\n"
            "Ingrese la fecha límite en formato dd-mm-aaaa",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue"), InlineKeyboardButton("Cancelar creación", callback_data="back")]])
        )
    else:
        await update.message.reply_text(
            "Puede ingresar una fecha límite de entrega para esta actividad, o presionar continuar para finalizar la creación.\n"
            "Ingrese la fecha límite en formato dd-mm-aaaa",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue"), InlineKeyboardButton("Cancelar creación", callback_data="back")]])
        )
    return states.T_ACTIVITY_SEND_DEADLINE
async def activity_deadline(update: Update, context: ContextTypes):
    """ Saves the deadline of the activity and creates it """
    query = update.callback_query
    date = None
    if query:
        await query.answer()
    else:
        date_str = update.message.text
        try:
            date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
        except ValueError:
            await update.message.reply_text(
                "Formato de fecha inválido. Ingrese la fecha límite en formato dd-mm-aaaa",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="continue"), InlineKeyboardButton("Cancelar creación", callback_data="back")]])
            )
            return states.T_ACTIVITY_SEND_DEADLINE

    context.user_data["activity"]["deadline"] = date

    # create activity
    activity_sql.add_activity(
        activity_type_id=context.user_data["activity"]["activity_type_id"],
        classroom_id=teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id,
        name=context.user_data["activity"]["type"],
        description=context.user_data["activity"]["description"],
        FileID=context.user_data["activity"]["FileID"],
        deadline=context.user_data["activity"]["deadline"],
    )
    logger.info(f"Activity {context.user_data['activity']['type']} created by {update.effective_user.id}")

    # go back to activity type (T_ACTIVITIES_CREATE_TYPE)
    activity_type_id = context.user_data['activity']['activity_type_id']
    activity_type = activity_type_sql.get_activity_type(activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    # should have single_submission=True
    text = f"Tipo de actividad: {token_type.type}\n" + f"{'Actividad grupal' if activity_type.guild_activity else 'Actividad individual'}\n"
    if activity_type.description:
        text += f"Descripción: {activity_type.description}\n"
    text += "\nEste tipo de actividad permite crear actividades específicas. Puede crearlas a continuación o acceder a las existentes.\n"

    activities = activity_sql.get_activities_by_activity_type_id(activity_type_id) # should have at least 1

    # Show activities with pagination.
    # Add buttons for back and create activity type
    buttons = [InlineKeyboardButton(f"{i}. {token_sql.get_token(activity.token_id).name}", callback_data=f"activity#{activity.id}") for i, activity in enumerate(activities, start=1)]
    other_buttons = [
        InlineKeyboardButton(f"Crear actividad", callback_data=f"create_activity#{activity_type_id}"),
        InlineKeyboardButton("Cambiar descripción" , callback_data="activity_type_change_description"),
        InlineKeyboardButton("Enviar otro archivo", callback_data="activity_type_change_file"),
        InlineKeyboardButton("Ocultar actividad", callback_data="activity_type_hide"),
    ]
    if query:
        if activity_type.FileID:
            try:
                try:
                    await query.message.reply_photo(activity_type.FileID, caption="Actividad creada\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
                except BadRequest:
                    await query.message.reply_document(activity_type.FileID, caption="Actividad creada\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
            except BadRequest:
                await query.edit_message_text("Actividad creada\n\n" + "Se ha producido un error al enviar el archivo. Puede intentar editar el tipo de actividad para enviar otro archivo.\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
        else:
            await query.edit_message_text("Actividad creada\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
    else:
        if activity_type.FileID:
            try:
                try:
                    await update.message.reply_photo(activity_type.FileID, caption="Actividad creada\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
                except BadRequest:
                    await update.message.reply_document(activity_type.FileID, caption="Actividad creada\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
            except BadRequest:
                await update.message.reply_text("Actividad creada\n\n" + "Se ha producido un error al enviar el archivo. Puede intentar editar el tipo de actividad para enviar otro archivo.\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
        else:
            await update.message.reply_text("Actividad creada\n\n" + text, reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons))
    
    return states.T_ACTIVITIES_TYPE_INFO

async def activity_selected(update: Update, context: ContextTypes):
    """ Shows the details of the activity selected. 
    Allows editing name (token name), description (token description), 
    fileID and deadline.
    Also allows manually adding credits to students or guilds. Even if the 
    deadline has passed.
    """
    query = update.callback_query
    await query.answer()

    activity_id = int(query.data.split("#")[1])
    # Save activity id in context
    context.user_data['activity']['activity_id'] = activity_id

    activity = activity_sql.get_activity(activity_id)
    token = token_sql.get_token(activity.token_id)
    activity_type = activity_type_sql.get_activity_type(activity.activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    text = f"Actividad: {token.name} de {token_type.type}\n" + f"{'Actividad grupal' if activity_type.guild_activity else 'Actividad individual'}\n"
    if token.description:
        text += f"Descripción: {token.description}\n"
    if activity.submission_deadline:
        text += f"Fecha límite: {activity.submission_deadline.strftime('%d-%m-%Y')}\n"
    
    if activity.FileID:
        try:
            try:
                await query.message.reply_photo(activity.FileID, caption=text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_OPTIONS))
            except BadRequest:
                await query.message.reply_document(activity.FileID, caption=text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_OPTIONS))
        except BadRequest:
            await query.edit_message_text("Se ha producido un error al enviar el archivo. Puede intentar editar la actividad para enviar otro archivo.\n\n" + text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_OPTIONS))
    else:
        if query.message.caption:
            await query.edit_message_caption(text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_OPTIONS))
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_ACTIVITY_OPTIONS))

    return states.T_ACTIVITY_INFO
async def activity_edit_name(update: Update, context: ContextTypes):
    """ Asks the user for a new name """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            "Ingrese el nuevo nombre de la actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Ingrese el nuevo nombre de la actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_ACTIVITY_EDIT_NAME
async def activity_edit_name_done(update: Update, context: ContextTypes):
    activity_id = context.user_data['activity']['activity_id']
    new_name = update.message.text
    activity_sql.update_name(activity_id, new_name)
    logger.info(f"Activity {activity_id} name updated by {update.effective_user.id}")
    await update.message.reply_text(
        "Nombre actualizado!",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END
async def activity_edit_description(update: Update, context: ContextTypes):
    """ Asks the user for a new description """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            "Ingrese la nueva descripción de la actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Ingrese la nueva descripción de la actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_ACTIVITY_EDIT_DESCRIPTION
async def activity_edit_description_done(update: Update, context: ContextTypes):
    """ Updates the activity with the new description """
    activity_id = context.user_data['activity']['activity_id']
    new_description = update.message.text
    activity_sql.update_description(activity_id, new_description)
    logger.info(f"Activity {activity_id} description updated by {update.effective_user.id}")
    await update.message.reply_text(
        "Descripción actualizada!",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END
async def activity_edit_file(update: Update, context: ContextTypes):
    """ Asks the user to send a new file """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            "Envíe un nuevo archivo para esta actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Envíe un nuevo archivo para esta actividad",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_ACTIVITY_EDIT_FILE
async def activity_edit_file_done(update: Update, context: ContextTypes):
    """ Updates the activity with the new file id """
    activity_id = context.user_data['activity']['activity_id']
    file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id
    activity_sql.update_file(activity_id, fid)
    logger.info(f"Activity {activity_id} file updated by {update.effective_user.id}")
    await update.message.reply_text(
        "Archivo actualizado!",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END
async def activity_edit_deadline(update: Update, context: ContextTypes):
    """ Asks the user for a new deadline """
    query = update.callback_query
    await query.answer()

    if query.message.caption:
        await query.edit_message_caption(
            "Ingrese la nueva fecha límite de la actividad en formato dd-mm-aaaa",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    else:
        await query.edit_message_text(
            "Ingrese la nueva fecha límite de la actividad en formato dd-mm-aaaa",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
    return states.T_ACTIVITY_EDIT_DEADLINE
async def activity_edit_deadline_done(update: Update, context: ContextTypes):
    """ Updates the activity with the new deadline """
    date_str = update.message.text
    try:
        date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        await update.message.reply_text(
            "Formato de fecha inválido. Ingrese la fecha límite en formato dd-mm-aaaa",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]])
        )
        return states.T_ACTIVITY_EDIT_DEADLINE
    
    activity_id = context.user_data['activity']['activity_id']
    activity_sql.update_deadline(activity_id, date)
    logger.info(f"Activity {activity_id} deadline updated by {update.effective_user.id}")
    await update.message.reply_text(
        "Fecha límite actualizada!",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

async def review_activity(update: Update, context: ContextTypes):
    pass


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
            CallbackQueryHandler(activity_selected, pattern=r"^activity#"),
            paginator_handler,
            CallbackQueryHandler(activity_type_edit_description, pattern=r"^activity_type_change_description$"),
            CallbackQueryHandler(activity_type_edit_file, pattern=r"^activity_type_change_file$"),
            CallbackQueryHandler(activity_type_hide, pattern=r"^activity_type_hide$"),
            CallbackQueryHandler(create_activity, pattern=r"^create_activity#"),
        ],
        states.T_ACTIVITIES_TYPE_EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity_type_edit_description_done)],
        states.T_ACTIVITIES_TYPE_EDIT_FILE: [MessageHandler(filters.Document.ALL | filters.PHOTO, activity_type_edit_file_done)],

        states.T_ACTIVITY_SEND_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity_name)],
        states.T_ACTIVITY_SEND_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, activity_description),
            CallbackQueryHandler(activity_description, pattern=r"^continue$"),
            ],
        states.T_ACTIVITY_SEND_FILE: [
            MessageHandler(filters.Document.ALL | filters.PHOTO, activity_file),
            CallbackQueryHandler(activity_file, pattern=r"^continue$"),
            ],
        states.T_ACTIVITY_SEND_DEADLINE: [
            MessageHandler((filters.Regex(r"^\d{2}-\d{2}-\d{4}$") & filters.TEXT) & ~filters.COMMAND, activity_deadline),
            CallbackQueryHandler(activity_deadline, pattern=r"^continue$"),
            ],

        states.T_ACTIVITY_INFO: [
            CallbackQueryHandler(review_activity, pattern=r"^activity_review$"),
            CallbackQueryHandler(activity_edit_name, pattern=r"^activity_change_name$"),
            CallbackQueryHandler(activity_edit_description, pattern=r"^activity_change_description$"),
            CallbackQueryHandler(activity_edit_file, pattern=r"^activity_change_file$"),
            CallbackQueryHandler(activity_edit_deadline, pattern=r"^activity_change_deadline$"),
        ],
        states.T_ACTIVITY_EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity_edit_name_done)],
        states.T_ACTIVITY_EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity_edit_description_done)],
        states.T_ACTIVITY_EDIT_FILE: [MessageHandler(filters.Document.ALL | filters.PHOTO, activity_edit_file_done)],
        states.T_ACTIVITY_EDIT_DEADLINE: [MessageHandler((filters.Regex(r"^\d{2}-\d{2}-\d{4}$") & filters.TEXT) & ~filters.COMMAND, activity_edit_deadline_done)],
    },
    fallbacks=[
        CallbackQueryHandler(teacher_activities_back, pattern="back"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
    ],
    allow_reentry=True,
)

