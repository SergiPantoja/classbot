from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from utils.logger import logger
from bot.utils import states, keyboards
from bot.utils.inline_keyboard_pagination import paginated_keyboard, paginator, paginator_handler
from sql import user_sql, teacher_sql, classroom_sql, course_sql, student_sql, student_classroom_sql, teacher_classroom_sql


async def teacher_settings(update: Update, context: ContextTypes):
    """Teacher settings menu"""
    await update.message.reply_text(
        "Elige una opción:",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_SETTINGS, one_time_keyboard=True, resize_keyboard=True),
    )

async def back_to_teacher_menu(update: Update, context: ContextTypes):
    """Returns to teacher menu"""
    # if it is a query answer it 
    if update.callback_query:
        query = update.callback_query
        query.answer()

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.message.chat_id).id)
    # get active classroom from db
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    # get course name
    course_name = course_sql.get_course(classroom.course_id).name

    await update.message.reply_text(
        f"Bienvenido profe {user_sql.get_user_by_chatid(update.message.chat_id).fullname}!\n\n"
        f"Curso: {course_name}\n"
        f"Aula: {classroom.name}\n"
        f"Menu en construcción...",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )

    # Sanitize context.user_data
    if "edit_course" in context.user_data:
        context.user_data.pop("edit_course")

    return ConversationHandler.END



# Edit course conversation
async def edit_course(update: Update, context: ContextTypes):
    """ Entry point of the edit course conversation.
    Gives options for changing course name, deleting course, transfering
    ownership, check other (owned) courses to edit or go back to settings menu."""
    
    # If teacher owns the current course, show options to edit it
    # else show options to check other courses
    # If teacher owns no other courses, show option to go back to settings menu

    # create context.user_data["edit_course"]
    context.user_data["edit_course"] = {}

    # get active course from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.message.chat_id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    course = course_sql.get_course(classroom.course_id)
    
    # if onwer
    if teacher.id == course.teacher_id:
        logger.info(f"Teacher {teacher.id} owns course {course.id}")
        # save id of the course to edit
        context.user_data["edit_course"]["course_id"] = course.id
        # Show edit options
        await update.message.reply_text(
            f"Curso: {course.name}\n"
            "Elige una opción:",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_EDIT_COURSE),
        )
        return states.EDIT_COURSE_CHOOSE_OPTION
    else:
        logger.info(f"Teacher {teacher.id} does not own course {course.id}")
        # get courses owned by teacher
        courses = course_sql.get_courses_by_teacher(teacher.id)
        # show courses to edit if teacher owns any
        if courses:
            buttons = [InlineKeyboardButton(f"{i}. {course.name}", callback_data=f"COURSE#{course.id}") for i, course in enumerate(courses, start=1)]
            await update.message.reply_text(
                "Elige un curso:",
                reply_markup=paginated_keyboard(buttons, context=context),
            )
            return states.EDIT_COURSE_SELECT_COURSE
        # else notif and go back to menu
        else:
            await update.message.reply_text(
                "No tienes cursos para editar",
                reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_SETTINGS, one_time_keyboard=True, resize_keyboard=True),
            )

            # clear context.user_data["edit_course"] if exists
            if "edit_course" in context.user_data:
                context.user_data.pop("edit_course")
            
            return ConversationHandler.END

async def select_course(update: Update, context: ContextTypes):
    """Selects a course to edit"""
    query = update.callback_query
    query.answer()

    course_id = int(query.data.split("#")[1])
    course = course_sql.get_course(course_id)

    # save id of the course to edit
    context.user_data["edit_course"]["course_id"] = course.id

    # Show edit options
    await query.edit_message_text(
        f"Curso: {course.name}\n"
        "Elige una opción:",
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_EDIT_COURSE),
    )
    return states.EDIT_COURSE_CHOOSE_OPTION

async def choose_option(update: Update, context: ContextTypes):
    """Handles the option selected by the user"""
    query = update.callback_query
    query.answer()
    option = query.data

    teacher_id = user_sql.get_user_by_chatid(update.callback_query.message.chat_id).id

    if option == "option_other_courses":
        # get courses owned by teacher
        courses = course_sql.get_courses_by_teacher(teacher_id)
        # show courses to edit if teacher owns any
        if courses:
            buttons = [InlineKeyboardButton(f"{i}. {course.name}", callback_data=f"COURSE#{course.id}") for i, course in enumerate(courses, start=1)]
            await query.edit_message_text(
                "Elige un curso:",
                reply_markup=paginated_keyboard(buttons, context=context),
            )
            return states.EDIT_COURSE_SELECT_COURSE
        # else notif show edit options again
        else:
            await query.edit_message_text(
            f"No tienes más cursos para editar\n\n"
            "Elige una opción:",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_EDIT_COURSE),
            )
            return states.EDIT_COURSE_CHOOSE_OPTION
    
    elif option == "option_edit_course_name":
        # asks to input new name
        await query.message.reply_text(
            "Ingresa el nuevo nombre del curso:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return states.EDIT_COURSE_NAME

    elif option == "option_transfer_course":
        # Shows teachers to transfer course ownership to (only teachers that
        # teach the course/belong to some classroom of the course)

        # get course id
        course_id = context.user_data["edit_course"]["course_id"]
        # get teachers that teach the course (get classrooms of the course and
        # then get teachers of those classrooms)
        classrooms = classroom_sql.get_classrooms_by_course(course_id)
        teachers = []
        for classroom in classrooms:
            teachers.extend(teacher_sql.get_teachers_by_classroom(classroom.id))

        # remove duplicates using id
        teachers = list({teacher.id: teacher for teacher in teachers}.values())

        # get users to use the name
        teachers = [user_sql.get_user(teacher.id) for teacher in teachers]

        # show teachers to transfer course ownership to (use paginator)
        buttons = [InlineKeyboardButton(f"{i}. {teacher.fullname}", callback_data=f"transfer_course#{teacher.id}") for i, teacher in enumerate(teachers, start=1)]
        await query.edit_message_text(
            "Elige un profesor para transferir el curso:",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
        )

        return states.EDIT_COURSE_TRANSFER

    elif option == "option_delete_course":
        await query.edit_message_text(
            "¿Estás seguro que deseas eliminar el curso?\n"
            "Esta acción no se puede deshacer, perderá toda la información de "
            "aulas y estudiantes asociados al curso.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Eliminar", callback_data="delete_course_confirm")], [InlineKeyboardButton("Atrás", callback_data="option_edit_course_back")]]),
        )
        return states.DELETE_COURSE_CONFIRM

    elif option == "option_edit_course_back":
        # back to settings menu
        await query.message.reply_text(
            "Elija una opción:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_SETTINGS, one_time_keyboard=True, resize_keyboard=True),
        )

        # clear context.user_data["edit_course"] if exists
        if "edit_course" in context.user_data:
            context.user_data.pop("edit_course")
        
        return ConversationHandler.END

async def edit_course_name(update: Update, context: ContextTypes):
    # get name
    name = update.message.text
    # get course id
    course_id = context.user_data["edit_course"]["course_id"]
    # update course name
    course_sql.update_course_name(course_id, name)
    # get course
    course = course_sql.get_course(course_id)
    # notif
    await update.message.reply_text(
        f"Nombre cambiado a {course.name}\n\n"
        "Elija una opcion:",
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_EDIT_COURSE)
    )
    return states.EDIT_COURSE_CHOOSE_OPTION

async def delete_course_confirm(update: Update, context: ContextTypes):
    """If user confirms, remove course from db"""
    query = update.callback_query
    query.answer()

    # Check if the course to delete is the active one (if the active classroom
    # belongs to this course) to then log out the user after deletion.
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.callback_query.message.chat_id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    active_course = classroom.course_id == context.user_data["edit_course"]["course_id"]

    if query.data == "delete_course_confirm":
        # get course id
        course_id = context.user_data["edit_course"]["course_id"]
        # delete course
        course_sql.delete_course(course_id)

        if active_course:
            # clear context.user_data and log out user
            context.user_data.clear()
            # notif
            await query.message.reply_text(
                "Curso eliminado",
                reply_markup=ReplyKeyboardMarkup([["/start"]], one_time_keyboard=True, resize_keyboard=True),
            )
            return ConversationHandler.END

        # go back to teacher main menu
        await query.message.reply_text(
            "Curso eliminado",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_SETTINGS, one_time_keyboard=True, resize_keyboard=True),
        )
        # log if there is any classroom still asociated with the course
        if classroom_sql.get_classrooms_by_course(course_id):
            logger.warning(f"Classrooms still asociated with course {course_id}")
        
        return ConversationHandler.END

    else:
        # notif
        await query.edit_message_text(
            "Elige una opción:",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_EDIT_COURSE)
        )
        return states.EDIT_COURSE_CHOOSE_OPTION

async def transfer_course(update: Update, context: ContextTypes):
    """ Transfers course ownership to the selected teacher. If the course was
    the active one, the user is logged out. """
    query = update.callback_query
    query.answer()

    course_id = context.user_data["edit_course"]["course_id"]
    teacher_to_id = int(query.data.split("#")[1])

    # check if the course to transfer is the active one (if the active classroom
    # belongs to this course) to then log out the user after transfer.
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.callback_query.message.chat_id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    active_course = classroom.course_id == course_id

    # transfer course ownership
    course_sql.transfer_course(course_id, teacher_to_id)
    
    if active_course:
        # clear context.user_data and log out user
        context.user_data.clear()
        # notif
        await query.message.reply_text(
            "Curso transferido",
            reply_markup=ReplyKeyboardMarkup([["/start"]], one_time_keyboard=True, resize_keyboard=True),
        )
        return ConversationHandler.END
    # else go back to teacher main menu
    await query.message.reply_text(
        "Curso transferido",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_SETTINGS, one_time_keyboard=True, resize_keyboard=True),
    )
    # log if the course owner is not the selected teacher
    if course_sql.get_course(course_id).teacher_id != teacher_to_id:
        logger.warning(f"Course owner is not the selected teacher")
    
    return ConversationHandler.END

async def edit_course_back(update: Update, context: ContextTypes):
    """Returns to settings menu"""
    query = update.callback_query
    query.answer()

    await query.message.reply_text(
        "Elija una opción:",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_SETTINGS, one_time_keyboard=True, resize_keyboard=True),
    )

    # clear context.user_data["edit_course"] if exists
    if "edit_course" in context.user_data:
        context.user_data.pop("edit_course")

    return ConversationHandler.END



# Handlers
edit_course_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Editar curso$"), edit_course)],
    states={
        states.EDIT_COURSE_CHOOSE_OPTION: [CallbackQueryHandler(choose_option, pattern=r"^option_")],
        states.EDIT_COURSE_SELECT_COURSE: [
            CallbackQueryHandler(select_course, pattern=r"^(COURSE#|option_other_courses)"),
            paginator_handler
            ],
        states.EDIT_COURSE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_course_name)],
        states.DELETE_COURSE_CONFIRM: [CallbackQueryHandler(delete_course_confirm, pattern=r"^delete_course_confirm")],
        states.EDIT_COURSE_TRANSFER: [
            CallbackQueryHandler(transfer_course, pattern=r"^transfer_course"),
            paginator_handler
            ],
    },
    fallbacks=[
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu),
        CallbackQueryHandler(edit_course_back, pattern=r"^(option_edit_course_back|back)$"),
        ],
)


