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
from bot.utils import states, keyboards, bot_text
from bot.utils.inline_keyboard_pagination import paginated_keyboard, paginator_handler
from bot.utils.pagination import Paginator, text_paginator_handler
from bot.utils.clean_context import clean_student_context
from sql import user_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, student_sql, guild_token_sql, token_sql, student_token_sql, guild_sql, activity_type_sql, activity_sql
from bot.student_inventory import back_to_student_menu


async def student_activities(update: Update, context: ContextTypes):
    """ Student activities menu. 
    Show the student's activities. 
    Initially individual activity_types that are not hidden. Options to 
    show activities from a guild. 
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
    context.user_data["activity"] = {}

    query = update.callback_query
    if query:
        await query.answer()

    classroom_id = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_chat.id).id).active_classroom_id
    # get activity_types
    activity_types = activity_type_sql.get_activity_types(classroom_id)
    
    if query and query.data == "guild_activities":
        # filter by guild activities
        activity_types = [activity_type for activity_type in activity_types if activity_type.guild_activity]
    else: # if not query or query.data != "individual_activities":
        # filter by individual activities
        activity_types = [activity_type for activity_type in activity_types if not activity_type.guild_activity]
    
    if activity_types:
        # show activity_types with pagination
        buttons = [InlineKeyboardButton(f"{i}. {token_type_sql.get_token_type(activity_type.token_type_id).type}", callback_data=f"activity_type#{activity_type.id}") for i, activity_type in enumerate(activity_types, start=1)]
        other_buttons = [
            InlineKeyboardButton(f"{'🧑‍🎓 Ver actividades individuales' if query and (query.data == 'guild_activities') else '🎓 Ver actividades de gremio'}", callback_data="individual_activities" if query and (query.data == "guild_activities") else "guild_activities"),
        ]
        text = "Actividades de gremio" if query and (query.data == "guild_activities") else "Actividades individuales"
        if query:
            await query.edit_message_text(
                text,
                reply_markup=paginated_keyboard(buttons=buttons, context=context, add_back=True, other_buttons=other_buttons)
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=paginated_keyboard(buttons=buttons, context=context, add_back=True, other_buttons=other_buttons)
            )
    else:
        if query:
            await query.edit_message_text(
                "No hay actividades actualmente",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(f"{'🧑‍🎓 Ver actividades individuales' if query.data == 'guild_activities' else '🎓 Ver actividades de gremio'}", callback_data="individual_activities" if query.data == "guild_activities" else "guild_activities"),],
                        [InlineKeyboardButton("🔙", callback_data="back")],
                    ]
                )
            )
        else:
            await update.message.reply_text(
                "No hay actividades actualmente",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("🎓 Ver actividades de gremio", callback_data="guild_activities"),],
                        [InlineKeyboardButton("🔙", callback_data="back")],
                    ]
                )
            )
    return states.S_ACTIVITY_TYPE_SELECT

async def activity_type_selected(update: Update, context: ContextTypes):
    """ Shows the details of the selected activity_type. 
        If the activity_type doesn't allow specific activities, show a button 
        for the student to send a submission (create a pending).
        If the activity_type allows specific activities, show the activities
        that arent past deadline and the student or guild dont have the associated token.
    """
    query = update.callback_query
    await query.answer()

    activity_type_id = int(query.data.split("#")[1])
    # Save activity_type id in context
    context.user_data['activity']['activity_type_id'] = activity_type_id

    activity_type = activity_type_sql.get_activity_type(activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)

    if activity_type.single_submission:
        # Show activities that arent past deadline and the student or guild dont have the associated token.
        # get activities
        text = ""
        activities = activity_sql.get_activities_by_activity_type_id(activity_type_id)
        # filter by deadline
        activities = [activity for activity in activities if (activity.submission_deadline is None) or (activity.submission_deadline >= datetime.datetime.now())]
        # filter by token (depends if the activity_type is guild or individual)
        if activity_type.guild_activity:
            classroom_id = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id
            guild = guild_sql.get_guild_by_student(student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id).id, classroom_id)
            if guild:
                activities = [activity for activity in activities if not guild_token_sql.exists(guild.id, activity.token_id)]
            else: # student doesnt belong to a guild
                text += f"No perteneces a ningún gremio, por lo que no puedes enviar entregas para esta actividad\n\n"
                activities = None
        else:
            activities = [activity for activity in activities if not student_token_sql.exists(student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id).id, activity.token_id)]
        if activities:
            # show activities with pagination
            buttons = [InlineKeyboardButton(f"{i}. {token_sql.get_token(activity.token_id).name}", callback_data=f"activity#{activity.id}") for i, activity in enumerate(activities, start=1)]
            text = "Seleccione una actividad\n\n"
            if activity_type.FileID:
                try:
                    try:
                        await query.message.reply_photo(activity_type.FileID, caption=text, reply_markup=paginated_keyboard(buttons=buttons, context=context, add_back=True))
                    except BadRequest:
                        await query.message.reply_document(activity_type.FileID, caption=text, reply_markup=paginated_keyboard(buttons=buttons, context=context, add_back=True))
                except BadRequest:
                    await query.edit_message_text("Se ha producido un error al enviar el archivo.\n\n" + text, reply_markup=paginated_keyboard(buttons=buttons, context=context, add_back=True))
            else:
                await query.edit_message_text(text, reply_markup=paginated_keyboard(buttons=buttons, context=context, add_back=True))
            return states.S_ACTIVITY_SELECT
        else:
            # no activities available for the student or guild
            text += f"No hay actividades de {token_type.type} disponibles en este momento\n"
            # go back to activity_type_select dont edit the keyboard
            if activity_type.FileID:
                try:
                    try:
                        await query.message.reply_photo(activity_type.FileID, caption=text)
                    except BadRequest:
                        await query.message.reply_document(activity_type.FileID, caption=text)
                except BadRequest:
                    await query.edit_message_text("Se ha producido un error al enviar el archivo.\n\n" + text)
            else:
                await query.edit_message_text(text)
            return ConversationHandler.END       
       
    else:
        # doesnt support specific activities
        # show details and button to send submission
        text = f"Actividad: {token_type.type}\n" + f"{'Actividad grupal' if activity_type.guild_activity else 'Actividad individual'}\n"
        if activity_type.description:
            text += f"Descripción: {activity_type.description}\n"
        
        if activity_type.FileID:
            try:    
                try:
                    await query.message.reply_photo(activity_type.FileID, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="activity_type_send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
                except BadRequest:
                    await query.message.reply_document(activity_type.FileID, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="activity_type_send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
            except BadRequest:
                await query.edit_message_text("Se ha producido un error al enviar el archivo.\n\n" + text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="activity_type_send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="activity_type_send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
        return states.S_ACTIVITY_TYPE_SEND_SUBMISSION

async def activity_selected(update: Update, context: ContextTypes):
    """ Show activity details and button to send submission. """
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
                await query.message.reply_photo(activity.FileID, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
            except BadRequest:
                await query.message.reply_document(activity.FileID, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
        except BadRequest:
            await query.edit_message_text("Se ha producido un error al enviar el archivo.\n\n" + text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
    else:
        if query.message.caption:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Enviar entrega", callback_data="send_submission")], [InlineKeyboardButton("🔙", callback_data="back")]]))
    return states.S_ACTIVITY_SEND_SUBMISSION

async def activity_type_send_submission(update: Update, context: ContextTypes):
    """ Sends a pending to the teacher. Guild activities requiere student to
    belong to a guild. """
    query = update.callback_query
    await query.answer()

    activity_type_id = context.user_data['activity']['activity_type_id']
    activity_type = activity_type_sql.get_activity_type(activity_type_id)

    guild = None
    if activity_type.guild_activity:
        # check if student belongs to a guild
        student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
        classroom_id = student.active_classroom_id
        guild = guild_sql.get_guild_by_student(student.id, classroom_id)
        if not guild:
            if query.message.caption:
                await query.edit_message_caption(query.message.caption + "\n\nNo perteneces a ningún gremio, por lo que no puedes enviar entregas para esta actividad")
            else:
                await query.edit_message_text("No perteneces a ningún gremio, por lo que no puedes enviar entregas para esta actividad")
        
            return ConversationHandler.END
    
    # if guild save guild id in context
    context.user_data['activity']['guild_id'] = guild.id if guild else None

    # ask for submission
    if query.message.caption:
        await query.edit_message_caption(query.message.caption + "\n\nEnvía tu entrega. Puedes enviar texto, una imagen o un archivo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]]),)
    else:
        await query.edit_message_text("Envía tu entrega. Puedes enviar texto, una imagen o un archivo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]]),)
    return states.S_ACTIVITY_TYPE_SEND_SUBMISSION_DONE

async def activity_type_send_submission_done(update: Update, context: ContextTypes):
    """ Creates a pending of token_type of the activity_type. """

    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = student.active_classroom_id
    guild_id = context.user_data['activity']['guild_id']
    activity_type_id = context.user_data['activity']['activity_type_id']
    activity_type = activity_type_sql.get_activity_type(activity_type_id)
    token_type = token_type_sql.get_token_type(activity_type.token_type_id)
    guild_id = context.user_data['activity']['guild_id']
    guild = guild_sql.get_guild(guild_id) if guild_id else None
    
    # get file id if exists
    file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id
    
    text = f"{user_sql.get_user(student.id).fullname} ha enviado una entrega para la actividad {token_type.type}:\n" + f"{'Gremio: ' + guild.name if guild else ''}\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"

    # Create pending in DB
    pending_sql.add_pending(student_id=student.id, classroom_id=classroom_id, token_type_id=token_type.id, guild_id=guild_id, text=text, FileID=fid)
    logger.info(f"New activity_type f{token_type.type} pending created by student {user_sql.get_user(student.id).fullname}")
    # Send notification to notification channel of the classroom if it exists
    chan = classroom_sql.get_teacher_notification_channel_chat_id(classroom_id)
    if chan:
        try:
            await context.bot.send_message(
                chat_id=chan,
                text=f"El estudiante {user_sql.get_user(student.id).fullname} ha enviado una entrega para la actividad {token_type.type}:\n" + f"{'Gremio: ' + guild.name if guild else ''}\n",
            )
        except BadRequest:
            logger.exception(f"Failed to send message to notification channel {chan}.")

    # notify student
    await update.message.reply_text(
        "Enviado!",
        reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True)
    )
    return ConversationHandler.END

async def activity_send_submission(update: Update, context: ContextTypes):
    """ Sends a pending to the teacher. """
    query = update.callback_query
    await query.answer()

    activity_id = context.user_data['activity']['activity_id']
    activity = activity_sql.get_activity(activity_id)
    activity_type = activity_type_sql.get_activity_type(activity.activity_type_id)

    guild_id = None
    if activity_type.guild_activity:
        # get guild id
        student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
        classroom_id = student.active_classroom_id
        guild = guild_sql.get_guild_by_student(student.id, classroom_id)
        guild_id = guild.id if guild else None

    # if guild save guild id in context
    context.user_data['activity']['guild_id'] = guild_id

    # ask for submission
    if query.message.caption:
        await query.edit_message_caption(query.message.caption + "\n\nEnvía tu entrega. Puedes enviar texto, una imagen o un archivo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]]),)
    else:
        await query.edit_message_text("Envía tu entrega. Puedes enviar texto, una imagen o un archivo", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]]),)
    return states.S_ACTIVITY_SEND_SUBMISSION_DONE

async def activity_send_submission_done(update: Update, context: ContextTypes):
    """ Creates a pending of token_type of the activity_type and with the token_id
     of the activity. """
    query = update.callback_query
    if query:
        await query.answer()
    
    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = student.active_classroom_id
    guild_id = context.user_data['activity']['guild_id']
    activity_id = context.user_data['activity']['activity_id']
    activity = activity_sql.get_activity(activity_id)
    token = token_sql.get_token(activity.token_id)
    guild = guild_sql.get_guild(guild_id) if guild_id else None
    activity_type = activity_type_sql.get_activity_type(activity.activity_type_id)
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
        context.user_data['activity']['FileID'] = fid
        text = f"{user_sql.get_user(student.id).fullname} ha enviado una entrega para la actividad {token.name} de {token_type.type}:\n" + f"{'Gremio: ' + guild.name if guild else ''}\n" + f"{update.message.text if update.message.text else ''}" + f"{update.message.caption if update.message.caption else ''}"
        context.user_data['activity']['text'] = text

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
                "Ya has enviado una entrega para esta actividad. ¿Deseas actualizarla?",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Sí", callback_data="delete_pending")], [InlineKeyboardButton("🔴 No", callback_data="back")]]),
            )
            return states.S_ACTIVITY_SEND_SUBMISSION_DONE
    
    # Create pending in DB
    pending_sql.add_pending(student_id=student.id, classroom_id=classroom_id, token_type_id=token_type.id, token_id=token.id, guild_id=guild_id, text=context.user_data['activity']['text'], FileID=context.user_data['activity']['FileID'])
    logger.info(f"New activity f{token.name} of f{token_type.type} pending created by student {user_sql.get_user(student.id).fullname}")
    # Send notification to notification channel of the classroom if it exists
    chan = classroom_sql.get_teacher_notification_channel_chat_id(classroom_id)
    if chan:
        try:
            await context.bot.send_message(
                chat_id=chan,
                text=f"El estudiante {user_sql.get_user(student.id).fullname} ha enviado una entrega para la actividad {token.name} de {token_type.type}:\n" + f"{'Gremio: ' + guild.name if guild else ''}\n",
            )
        except BadRequest:
            logger.exception(f"Failed to send message to notification channel {chan}.")

    # notify student
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

async def student_activities_back(update: Update, context: ContextTypes):
    """ Back to student menu. """
    query = update.callback_query
    await query.answer()

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

    if "activity" in context.user_data:
        context.user_data.pop("activity")
    return ConversationHandler.END


# Handlers
student_activities_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📝 Actividades$"), student_activities)],
    states={
        states.S_ACTIVITY_TYPE_SELECT: [
            CallbackQueryHandler(student_activities, pattern=r"^(individual_activities|guild_activities)$"),
            CallbackQueryHandler(activity_type_selected, pattern=r"^activity_type#"),
            paginator_handler,
        ],
        states.S_ACTIVITY_SELECT: [
            CallbackQueryHandler(activity_selected, pattern=r"^activity#"),
            paginator_handler,
        ],
        states.S_ACTIVITY_TYPE_SEND_SUBMISSION: [
            CallbackQueryHandler(activity_type_send_submission, pattern=r"^activity_type_send_submission$"),
        ],
        states.S_ACTIVITY_TYPE_SEND_SUBMISSION_DONE: [
            MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, activity_type_send_submission_done)
        ],
        states.S_ACTIVITY_SEND_SUBMISSION: [
            CallbackQueryHandler(activity_send_submission, pattern=r"^send_submission$"),
        ],
        states.S_ACTIVITY_SEND_SUBMISSION_DONE: [
            MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, activity_send_submission_done),
            CallbackQueryHandler(activity_send_submission_done, pattern=r"^delete_pending$"),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(student_activities_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^🔙$"), back_to_student_menu),
    ],
    allow_reentry=True,
)
