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
from bot.utils.clean_context import clean_teacher_context
from sql import user_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, student_sql, guild_token_sql, token_sql, student_token_sql, guild_sql, activity_type_sql, activity_sql, practic_class_sql, practic_class_exercises_sql
from bot.teacher_settings import back_to_teacher_menu


async def teacher_classroom(update: Update, context: ContextTypes):
    """ Teacher classroom menu. Here the teacher can see the classroom's students,
    guilds and send messages to all students in the classroom. """

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
    
    await update.message.reply_text(
        "Selecciona una opción",
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_CLASSROOM),
    )
    return states.T_CLASSROOM_OPTION

async def send_message(update: Update, context: ContextTypes):
    """ Sends a message to all students in the classroom. Supports sending
    photo or document as well."""
    query = update.callback_query
    await query.answer()

    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)

    await query.edit_message_text(
        f"Envía una notificación a todos los estudiantes de <b>{classroom.name}</b>.\n\nPuedes enviar un archivo o una foto, o simplemente un mensaje de texto.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]]),
        parse_mode="HTML",
    )
    return states.T_CLASSROOM_SEND_MESSAGE

async def send_message_done(update: Update, context: ContextTypes):
    """ Receives the message to send to the students and sends it. """
    file = update.message.document or update.message.photo
    fid = None
    if file:
        if update.message.document:
            fid = file.file_id
        else:
            fid = file[-1].file_id

    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)

    teacher_name = user_sql.get_user(teacher.id).fullname
    text = f"<b>Mensaje de {teacher_name}:</b>\n<b>Aula - {classroom.name}</b>\n\n<i>{update.message.text if update.message.text else ''}</i>" + f"<i>{update.message.caption if update.message.caption else ''}</i>"

    # get students from db
    students = student_sql.get_students_by_classroom(classroom.id)

    # send message to all students
    for student in students:
        chat_id = user_sql.get_user(student.id).telegram_chatid
        try:
            if fid:
                try:
                    try:
                        await context.bot.send_photo(photo=fid, chat_id=chat_id, caption=text, parse_mode="HTML")
                    except BadRequest:
                        await context.bot.send_document(document=fid, chat_id=chat_id, caption=text, parse_mode="HTML")
                except BadRequest:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode="HTML",
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                )
        except BadRequest as e:
            logger.error(f"Error sending message to student {student.id}: {e}")
            await update.message.reply_text(
                f"Error enviando mensaje a {user_sql.get_user(student.id).fullname}",
            )
    
    await update.message.reply_text(
        "Mensajes enviados",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )

    return ConversationHandler.END

async def classroom_students(update: Update, context: ContextTypes):
    """ Shows all students of the classroom ordered by amount of credits.
    Supports pagination. Each line shows the amount of credits, the student
    name and has a command in the form '/student_id' to see the student's
    credits history. """
    query = update.callback_query
    await query.answer()

    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    classroom_id = classroom.id
    students = student_sql.get_students_by_classroom(classroom.id)

    # sort students by total credits
    students.sort(key=lambda student: student_token_sql.get_total_value_by_classroom(student.id, classroom_id), reverse=True)
    # create lines for paginator 
    lines = [f"{i}. {str(student_token_sql.get_total_value_by_classroom(student.id, classroom_id)).ljust(10)} ➡️ {user_sql.get_user(student.id).fullname} /student_{student.id}" for i, student in enumerate(students, start=1)]
    # create new paginator using this lines
    paginator = Paginator(
        lines=lines, 
        items_per_page=10, 
        text_before=f"Estudiantes de <b>{classroom.name}</b> ordenados por créditos:", 
        text_after="Selecciona un estudiante para ver su historial de créditos",
        add_back=True,
        )
    # save paginator in context
    context.user_data["paginator"] = paginator
    # send first page
    await query.edit_message_text(
        paginator.text(),
        reply_markup=paginator.keyboard(),
        parse_mode="HTML",
    )
    return states.T_CLASSROOM_STUDENT_INFO

async def classroom_guilds(update: Update, context: ContextTypes):
    """ Shows all guilds of the classroom ordered by amount of credits.
    Supports pagination. Each line shows the amount of credits, the guild
    name and has a command in the form '/guild_id' to see the guild's
    students and credits history. """
    query = update.callback_query
    await query.answer()

    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    classroom_id = classroom.id
    guilds = guild_sql.get_guilds_by_classroom(classroom.id)

    # sort guilds by total credits
    guilds.sort(key=lambda guild: guild_token_sql.get_total_value_by_classroom(guild.id, classroom_id), reverse=True)
    # create lines for paginator
    lines = [f"{i}. {str(guild_token_sql.get_total_value_by_classroom(guild.id, classroom_id)).ljust(10)} ➡️ {guild.name} /guild_{guild.id}" for i, guild in enumerate(guilds, start=1)]
    # create new paginator using this lines
    paginator = Paginator(
        lines=lines, 
        items_per_page=10, 
        text_before=f"Gremios de <b>{classroom.name}</b> ordenados por créditos:", 
        text_after="Selecciona un gremio para ver su historial de créditos",
        add_back=True,
        )
    # save paginator in context
    context.user_data["paginator"] = paginator
    # send first page
    await query.edit_message_text(
        paginator.text(),
        reply_markup=paginator.keyboard(),
        parse_mode="HTML",
    )
    return states.T_CLASSROOM_GUILD_INFO

async def guild_info(update: Update, context: ContextTypes):
    """ Shows the guild credits history per day from the most recent.
    Supports pagination. Each line has the date - the amount of credits,
    the token name and the token_type type if it its related activity_type
    has single_submission set to True. The first line shows the guild's
    students ordered by amount of credits."""
    guild_id = int(update.message.text.split("_")[1])
    guild = guild_sql.get_guild(guild_id)
    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    classroom_id = classroom.id

    # get guild's students
    students = student_sql.get_students_by_guild(guild.id)
    # sort students by total credits
    students.sort(key=lambda student: student_token_sql.get_total_value_by_classroom(student.id, classroom_id), reverse=True)
    # create first lines using students
    lines = [f"Estudiantes de <b>{guild.name}</b> ordenados por créditos:"]
    student_lines = [f"{i}. {str(student_token_sql.get_total_value_by_classroom(student.id, classroom_id)).ljust(10)} ➡️ {user_sql.get_user(student.id).fullname} /student_{student.id}" for i, student in enumerate(students, start=1)]
    lines.extend(student_lines)
    lines.append("")
    lines.append(f"Créditos:")

    # get guild's tokens from db
    guild_tokens = guild_token_sql.get_guild_tokens_by_guild_and_classroom(guild_id, classroom_id) # already sorted
    # create lines for paginator
    i = 1
    for guild_token in guild_tokens:
        token = token_sql.get_token(guild_token.token_id)
        token_type = token_type_sql.get_token_type(token.token_type_id)
        # if not default token_type (default token_types havee classroom_id = None and no activity_type_id)
        if token_type.classroom_id:
            activity_type = activity_type_sql.get_activity_type_by_token_type_id(token_type.id)
            if activity_type.single_submission:
                lines.append(f"{i}. {guild_token.creation_date.strftime('%d/%m/%Y')} - {str(guild_token.value).ljust(10)} ➡️ <b>{token.name}</b> de <i>{token_type.type}</i>")
            else:
                lines.append(f"{i}. {guild_token.creation_date.strftime('%d/%m/%Y')} - {str(guild_token.value).ljust(10)} ➡️ <b>{token.name}</b>")
        else:
            lines.append(f"{i}. {guild_token.creation_date.strftime('%d/%m/%Y')} - {str(guild_token.value).ljust(10)} ➡️ <b>{token.name}</b>")
        i += 1
    # create new paginator using this lines
    paginator = Paginator(
        lines=lines, 
        items_per_page=10, 
        text_before=f"Historial de créditos de <b>{guild.name}:</b>", 
        text_after="",
        add_back=True,
        )
    # save paginator in context
    context.user_data["paginator"] = paginator
    # send first page
    await update.message.reply_text(
        paginator.text(),
        reply_markup=paginator.keyboard(),
        parse_mode="HTML",
    )
    return states.T_CLASSROOM_GUILD_INFO

async def student_info(update: Update, context: ContextTypes):
    """ Shows the student's credits history per day from the most recent.
    Supports pagination. Each line has the date - the amount of credits, 
    the token name and the token_type type if it its related activity_type
    has single_submission set to True. """
    student_id = int(update.message.text.split("_")[1])
    # get student from db
    student = student_sql.get_student(student_id)
    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    classroom_id = classroom.id
    # get student's tokens from db
    student_tokens = student_token_sql.get_student_token_by_student_and_classroom(student_id, classroom_id) # already sorted
    # create lines for paginator
    lines = []
    i = 1
    for student_token in student_tokens:
        token = token_sql.get_token(student_token.token_id)
        token_type = token_type_sql.get_token_type(token.token_type_id)
        # if not default token_type (default token_types havee classroom_id = None and no activity_type_id)
        if token_type.classroom_id:
            activity_type = activity_type_sql.get_activity_type_by_token_type_id(token_type.id)
            if activity_type.single_submission:
                lines.append(f"{i}. {student_token.creation_date.strftime('%d/%m/%Y')} - {str(student_token.value).ljust(10)} ➡️ <b>{token.name}</b> de <i>{token_type.type}</i>")
            else:
                lines.append(f"{i}. {student_token.creation_date.strftime('%d/%m/%Y')} - {str(student_token.value).ljust(10)} ➡️ <b>{token.name}</b>")
        else:
            lines.append(f"{i}. {student_token.creation_date.strftime('%d/%m/%Y')} - {str(student_token.value).ljust(10)} ➡️ <b>{token.name}</b>")
        i += 1
    # create new paginator using this lines
    other_buttons = [InlineKeyboardButton("➕ Asignar créditos", callback_data=f"assign_credits_{student.id}")]
    paginator = Paginator(
        lines=lines, 
        items_per_page=10, 
        text_before=f"Historial de créditos de <b>{user_sql.get_user(student.id).fullname}:</b>", 
        text_after="",
        add_back=True,
        other_buttons=other_buttons,
        )
    # save paginator in context
    context.user_data["paginator"] = paginator
    # send first page
    await update.message.reply_text(
        paginator.text(),
        reply_markup=paginator.keyboard(),
        parse_mode="HTML",
    )
    return states.T_CLASSROOM_STUDENT_INFO

async def assign_credits_to_student(update: Update, context: ContextTypes):
    """ Asks the teacher how many credits to assign to the student and an 
    optional comment. """
    query = update.callback_query
    await query.answer()

    student_id = int(update.callback_query.data.split("_")[2])
    # save in context
    if "classroom" not in context.user_data:
        context.user_data["classroom"] = {}
    context.user_data["classroom"]["student_id"] = student_id
    student = student_sql.get_student(student_id)

    await update.callback_query.edit_message_text(
        f"¿Cuántos créditos deseas asignar a {user_sql.get_user(student.id).fullname}?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back")]]),
    )
    return states.T_CLASSROOM_ASSIGN_CREDITS_STUDENT

async def assign_credits_to_student_done(update: Update, context: ContextTypes):
    """ Assigns the credits to the student """

    # get student from db
    student_id = context.user_data["classroom"]["student_id"]
    student = student_sql.get_student(student_id)
    student_name = user_sql.get_user(student.id).fullname
    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    teacher_name = user_sql.get_user(teacher.id).fullname
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    classroom_id = classroom.id

    text = update.message.text
    # get token value and comment
    try:
        value = int(text.split(" ")[0])
        comment = text.split(" ", 1)[1]
    except:
        value = int(text)
        comment = None
    
    token_type = token_type_sql.get_token_type_by_type("Créditos otorgados directamente")
    # Create new token
    token_sql.add_token(name=f"{token_type.type} a {student_name} por {teacher_name}", token_type_id=token_type.id, classroom_id=classroom_id, description=comment)
    token_id = token_sql.get_last_token().id
    # assign token to student
    student_token_sql.add_student_token(student_id=student.id, token_id=token_id, value=value, teacher_id=teacher.id)
    logger.info(f"Teacher {teacher.id} assigned {value} credits to student {student.id} in classroom {classroom.id}")
    # Create approved pending
    text = f"Créditos otorgados directamente a {student_name} por {teacher_name}"
    pending_sql.add_pending(student_id=student.id, classroom_id=classroom_id, token_type_id=token_type.id, token_id=token_id, status="APPROVED", approved_by=teacher.id, text=text)

    # Notify student
    text = f"<b>{teacher_name}</b> te ha otorgado <b>{value}</b> créditos"
    if comment:
        text += f"\n\n<b>Comentario:</b>\n{comment}"
    
    try:
        await context.bot.send_message(
            chat_id=user_sql.get_user(student.id).telegram_chatid,
            text=text,
            parse_mode="HTML",
        )
    except BadRequest:
        logger.error(f"Error sending message to student {student_name}")

    await update.message.reply_text(
        f"Créditos asignados a {user_sql.get_user(student.id).fullname}",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

async def teacher_classroom_back(update: Update, context: ContextTypes):
    """ Go back to teacher main menu """
    query = update.callback_query
    await query.answer()

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    # get active classroom from db
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    # get course name
    course_name = course_sql.get_course(classroom.course_id).name

    await query.message.reply_text(
        bot_text.main_menu(
            fullname=user_sql.get_user(teacher.id).fullname,
            role="teacher",
            classroom_name=classroom.name,
        ),
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="HTML",
    )

    if "classroom" in context.user_data:
        context.user_data.pop("classroom")
    return ConversationHandler.END


# Handlers
teacher_classroom_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(r"^🏫 Aula$"), teacher_classroom)],
    states={
        states.T_CLASSROOM_OPTION:[
            text_paginator_handler,
            CallbackQueryHandler(send_message, pattern=r"^classroom_send_message$"),
            CallbackQueryHandler(classroom_students, pattern=r"^classroom_students$"),
            CallbackQueryHandler(classroom_guilds, pattern=r"^classroom_guilds$"),
        ],
        states.T_CLASSROOM_SEND_MESSAGE:[MessageHandler(filters.TEXT | filters.Document.ALL | filters.PHOTO, send_message_done)],
        states.T_CLASSROOM_GUILD_INFO:[
            MessageHandler(filters.TEXT & filters.Regex(r"^/guild_\d+$"), guild_info),
            MessageHandler(filters.TEXT & filters.Regex(r"^/student_\d+$"), student_info),
            text_paginator_handler,
        ],
        states.T_CLASSROOM_STUDENT_INFO:[
            MessageHandler(filters.TEXT & filters.Regex(r"^/student_\d+$"), student_info),
            text_paginator_handler,
            CallbackQueryHandler(assign_credits_to_student, pattern=r"^assign_credits_\d+$"),
        ],
        states.T_CLASSROOM_ASSIGN_CREDITS_STUDENT:[MessageHandler(filters.Regex(r"^\d+(\s.*)?") & ~filters.COMMAND, assign_credits_to_student_done)],
    },
    fallbacks=[
        CallbackQueryHandler(teacher_classroom_back, pattern="back"),
        MessageHandler(filters.Regex("^🔙$"), back_to_teacher_menu),
    ],
    allow_reentry=True,
)


