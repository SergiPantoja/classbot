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
from bot.utils.clean_context import clean_teacher_context
from sql import user_sql, teacher_sql, classroom_sql, course_sql, guild_sql, student_sql, student_guild_sql, guild_token_sql, pending_sql, token_type_sql, teacher_classroom_sql, token_sql, student_token_sql
from bot.teacher_settings import back_to_teacher_menu


async def teacher_guilds(update: Update, context: ContextTypes):
    """ Shows the guilds in the current classroom with pagination, allows for 
    the creation of a new guild"""
    # Sanitize context.user_data
    clean_teacher_context(context)

    context.user_data["guild"] = {}

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

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    guilds = guild_sql.get_guilds_by_classroom(classroom_id)

    if guilds:
        # Show guilds with pagination
        buttons = [InlineKeyboardButton(f"{i}. {guild.name}", callback_data=f"guild#{guild.id}") for i, guild in enumerate(guilds, start=1)]
        other_buttons = [InlineKeyboardButton("Crear gremio", callback_data="create_guild")]
        await update.message.reply_text(
            "Gremios del aula:",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
        )
        return states.T_GUILD_SELECT

    else:
        # No guilds in classroom
        await update.message.reply_text(
            "No hay gremios en esta aula, desea crear uno?",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_GUILD),
        )
        return states.T_GUILD_CREATE
    
async def teacher_guilds_create(update: Update, context: ContextTypes):
    # ask for guild name
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Ingrese el nombre del gremio:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
    )
    return states.T_GUILD_CREATE_NAME

async def teacher_guilds_create_name(update: Update, context: ContextTypes):
    """ Creates the guild with the given name, then show the guilds """
    name = update.message.text
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    # create guild
    guild_sql.add_guild(classroom_id, name)
    logger.info(f"Teacher {teacher.id} created guild {name} in classroom {classroom_id}")
    
    # get guilds
    guilds = guild_sql.get_guilds_by_classroom(classroom_id)
    # show guilds with pagination
    buttons = [InlineKeyboardButton(f"{i}. {guild.name}", callback_data=f"guild#{guild.id}") for i, guild in enumerate(guilds, start=1)]
    other_buttons = [InlineKeyboardButton("Crear gremio", callback_data="create_guild")]
    await update.message.reply_text(
        "Gremios del aula:",
        reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
    )
    return states.T_GUILD_SELECT

async def select_guild(update: Update, context: ContextTypes):
    """ Selects the guild and shows the students and the options """
    query = update.callback_query
    await query.answer()

    if query.data == "create_guild":
        await query.message.reply_text(
            "Ingrese el nombre del gremio:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.T_GUILD_CREATE_NAME

    else:
        """ Shows the students in this guild and options to interact with the guild """
        guild_id = int(query.data.split("#")[1])
        guild = guild_sql.get_guild(guild_id)
        # save id in context
        context.user_data["guild"]["id"] = guild_id
        # get students in guild
        students = student_sql.get_students_by_guild(guild_id)

        if students:
            student_text = "\n".join([f"{i}. {user_sql.get_user(student.id).fullname}" for i, student in enumerate(students, start=1)])
        else:
            student_text = "No hay estudiantes en este gremio"
        
        text = f"Gremio: {guild.name}\n\nEstudiantes:\n{student_text}"
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_GUILD_OPTIONS),
        )
        return states.T_GUILD_OPTIONS

async def guild_options(update: Update, context: ContextTypes):
    """ Manages the options for the guild """
    query = update.callback_query
    await query.answer()

    if query.data == "guild_add_student":
        # get students not in any guild and in the active classroom of the teacher
        teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
        classroom_id = teacher.active_classroom_id
        # get students in classroom
        students = student_sql.get_students_by_classroom(classroom_id)
        # get students in any guild in this classroom
        guilds = guild_sql.get_guilds_by_classroom(classroom_id)
        students_in_guilds = []
        for guild in guilds:
            students_in_guilds.extend(student_sql.get_students_by_guild(guild.id))
        # remove students in guilds with the same id as students in students list
        students = [student for student in students if student.id not in [student_in_guild.id for student_in_guild in students_in_guilds]]

        if students:
            buttons = [InlineKeyboardButton(f"{i}. {user_sql.get_user(student.id).fullname}", callback_data=f"add_student#{student.id}") for i, student in enumerate(students, start=1)]
            await query.edit_message_text(
                text="Seleccione el estudiante a añadir:",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
            )
            return states.T_GUILD_SELECT_STUDENT_TO_ADD
        else:
            await query.edit_message_text(
                text="No hay estudiantes para añadir",
                reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_GUILD_OPTIONS),
            )
            return states.T_GUILD_OPTIONS

    elif query.data == "guild_remove_student":
        # get students in this guild
        guild_id = context.user_data["guild"]["id"]
        students = student_sql.get_students_by_guild(guild_id)

        if students:
            buttons = [InlineKeyboardButton(f"{i}. {user_sql.get_user(student.id).fullname}", callback_data=f"remove_student#{student.id}") for i, student in enumerate(students, start=1)]
            await query.edit_message_text(
                text="Seleccione el estudiante a eliminar:",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
            )
            return states.T_GUILD_SELECT_STUDENT_TO_REMOVE
        else:
            await query.edit_message_text(
                text="No hay estudiantes para eliminar",
                reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_GUILD_OPTIONS),
            )
            return states.T_GUILD_OPTIONS

    elif query.data == "guild_delete":
        # delete guild and show guilds
        guild_id = context.user_data["guild"]["id"]
        guild_sql.delete_guild(guild_id)
        # get guilds
        guilds = guild_sql.get_guilds_by_classroom(teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id).active_classroom_id)
        if guilds:
            # Show guilds with pagination
            buttons = [InlineKeyboardButton(f"{i}. {guild.name}", callback_data=f"guild#{guild.id}") for i, guild in enumerate(guilds, start=1)]
            other_buttons = [InlineKeyboardButton("Crear gremio", callback_data="create_guild")]
            await query.edit_message_text(
                "Gremios del aula:",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True, other_buttons=other_buttons),
            )
            return states.T_GUILD_SELECT
        else:
            # No guilds in classroom
            await query.edit_message_text(
                "No hay gremios en esta aula, desea crear uno?",
                reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_GUILD),
            )
            return states.T_GUILD_CREATE

    elif query.data == "guild_change_name":
        await query.message.reply_text(
            "Ingrese el nuevo nombre:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.T_GUILD_OPTIONS_EDIT_NAME
    
    elif query.data == "guild_credit_details":
        # show credit details
        pass

async def edit_guild_name(update: Update, context: ContextTypes):
    """ Edits the name of the guild """
    name = update.message.text

    guild_id = context.user_data["guild"]["id"]
    guild_sql.update_guild_name(guild_id, name)
    
    guild = guild_sql.get_guild(guild_id)

    # get students in guild
    students = student_sql.get_students_by_guild(guild_id)

    if students:
        student_text = "\n".join([f"{i}. {user_sql.get_user(student.id).fullname}" for i, student in enumerate(students, start=1)])
    else:
        student_text = "No hay estudiantes en este gremio"
    
    text = f"Gremio: {guild.name}\n\nEstudiantes:\n{student_text}"
    await update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_GUILD_OPTIONS),
    )
    return states.T_GUILD_OPTIONS

async def select_student_to_add(update: Update, context: ContextTypes):
    """ Adds the student to the guild """
    query = update.callback_query
    query.answer()

    student_id = int(query.data.split("#")[1])
    guild_id = context.user_data["guild"]["id"]

    # add student to guild
    student_guild_sql.add_student_guild(student_id, guild_id)

    # get students in guild
    students = student_sql.get_students_by_guild(guild_id)

    if students:
        student_text = "\n".join([f"{i}. {user_sql.get_user(student.id).fullname}" for i, student in enumerate(students, start=1)])
    else:
        student_text = "No hay estudiantes en este gremio"
    
    text = f"Gremio: {guild_sql.get_guild(guild_id).name}\n\nEstudiantes:\n{student_text}"
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_GUILD_OPTIONS),
    )
    return states.T_GUILD_OPTIONS

async def select_student_to_remove(update: Update, context: ContextTypes):
    """ Removes the student from the guild """
    query = update.callback_query
    query.answer()

    student_id = int(query.data.split("#")[1])
    guild_id = context.user_data["guild"]["id"]

    # remove student from guild
    student_guild_sql.remove_student(student_id, guild_id)

    # get students in guild
    students = student_sql.get_students_by_guild(guild_id)

    if students:
        student_text = "\n".join([f"{i}. {user_sql.get_user(student.id).fullname}" for i, student in enumerate(students, start=1)])
    else:
        student_text = "No hay estudiantes en este gremio"
    
    text = f"Gremio: {guild_sql.get_guild(guild_id).name}\n\nEstudiantes:\n{student_text}"
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_GUILD_OPTIONS),
    )
    return states.T_GUILD_OPTIONS

async def teacher_guilds_back(update: Update, context: ContextTypes):
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

    if "guild" in context.user_data:
        context.user_data.pop("guild")
    return ConversationHandler.END


# Handlers
teacher_guilds_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Gremios$"), teacher_guilds)],
    states={
        states.T_GUILD_CREATE: [CallbackQueryHandler(teacher_guilds_create, pattern=r"^create_guild$")],
        states.T_GUILD_SELECT: [
            CallbackQueryHandler(select_guild, pattern=r"^(guild#|create_guild)"),
            paginator_handler,
        ],
        states.T_GUILD_CREATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_guilds_create_name)],
        states.T_GUILD_OPTIONS: [CallbackQueryHandler(guild_options, pattern=r"^guild_")],
        states.T_GUILD_OPTIONS_EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_guild_name)],
        states.T_GUILD_SELECT_STUDENT_TO_ADD: [
            CallbackQueryHandler(select_student_to_add, pattern=r"^add_student#"),
            paginator_handler,
        ],
        states.T_GUILD_SELECT_STUDENT_TO_REMOVE: [
            CallbackQueryHandler(select_student_to_remove, pattern=r"^remove_student#"),
            paginator_handler,
        ],
    },
    fallbacks=[
        CallbackQueryHandler(teacher_guilds_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
        ],
    allow_reentry=True,
)
