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
from bot.utils.inline_keyboard_pagination import paginated_keyboard, paginator_handler
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
        # check if the classrooms of the course got deleted in cascade
        if classroom_sql.get_classrooms_by_course(course_id):
            logger.warning(f"Classrooms of course {course_id} were not deleted\n\n\n\n")

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


# Edit classroom conversation
async def edit_classroom(update: Update, context: ContextTypes):
    """Entry point of the edit classroom conversation.
    Gives options for changing name, passwords, removing students, and if user
    is onwer of the course this classroom belongs to, deleting the classroom
    and removing teachers."""

    # create context.user_data["edit_classroom"]
    context.user_data["edit_classroom"] = {}

    # get active classroom from db
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.message.chat_id).id)
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)

    # check if teacher is owner of the course to choose which keyboard to show
    course = course_sql.get_course(classroom.course_id)
    keyboard = keyboards.TEACHER_EDIT_CLASSROOM_OWNER if teacher.id == course.teacher_id else keyboards.TEACHER_EDIT_CLASSROOM

    await update.message.reply_text(
        f"Aula: {classroom.name}\n"
        "Elige una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return states.EDIT_CLASSROOM_CHOOSE_OPTION

async def edit_classroom_choose_option(update: Update, context: ContextTypes):
    """Handles the option selected by the user"""
    query = update.callback_query
    query.answer()
    option = query.data

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.callback_query.message.chat_id).id)
    course = course_sql.get_course(classroom_sql.get_classroom(teacher.active_classroom_id).course_id)
    keyboard = keyboards.TEACHER_EDIT_CLASSROOM_OWNER if teacher.id == course.teacher_id else keyboards.TEACHER_EDIT_CLASSROOM
    
    if option == "option_edit_classroom_name":
        # asks to input new name
        await query.message.reply_text(
            "Ingresa el nuevo nombre del aula:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return states.EDIT_CLASSROOM_NAME
    
    elif option == "option_edit_classroom_passwords":
        # asks to choose between teacher and student password
        await query.edit_message_text(
            "Cuál contraseña desea cambiar?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Profesor", callback_data="option_edit_teacher_password")], [InlineKeyboardButton("Estudiante", callback_data="option_edit_student_password")], [InlineKeyboardButton("Atrás", callback_data="option_edit_classroom_back")]]),
        )
        return states.EDIT_CLASSROOM_CHOOSE_OPTION
    elif option == "option_edit_teacher_password":
        # asks to input new password
        context.user_data["edit_classroom"]["password_type"] = "teacher_auth"
        await query.message.reply_text(
            "Ingresa la nueva contraseña de profesor:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return states.EDIT_CLASSROOM_PASSWORD
    elif option == "option_edit_student_password":
        # asks to input new password
        context.user_data["edit_classroom"]["password_type"] = "student_auth"
        await query.message.reply_text(
            "Ingresa la nueva contraseña de estudiante:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return states.EDIT_CLASSROOM_PASSWORD
        
    elif option == "option_change_classroom":
        # get classroom ids the teacher is in
        classrooms = teacher_classroom_sql.get_classroom_ids(teacher.id)
        # remove active classroom
        classrooms.remove(teacher.active_classroom_id)
        if classrooms:
            # show classrooms to change to
            buttons = [InlineKeyboardButton(f"{i}. {classroom_sql.get_classroom(classroom_id).name}", callback_data=f"change_classroom#{classroom_id}") for i, classroom_id in enumerate(classrooms, start=1)]
            await query.edit_message_text(
                "Elige un aula:",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
            )
            return states.EDIT_CLASSROOM_CHANGE
        else:
            # notif
            await query.edit_message_text(
                "No tienes más aulas para cambiar\n\n"
                "Elija una opción:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return states.EDIT_CLASSROOM_CHOOSE_OPTION
    
    elif option == "option_remove_students":
        # show students in the classroom to remove
        student_ids = student_classroom_sql.get_student_ids(teacher.active_classroom_id)
        if student_ids:
            buttons = [InlineKeyboardButton(f"{i}. {user_sql.get_user(student_id).fullname}", callback_data=f"remove_student#{student_id}") for i, student_id in enumerate(student_ids, start=1)]
            await query.edit_message_text(
                "Elige un estudiante:",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
            )
            return states.EDIT_CLASSROOM_REMOVE_STUDENT
        else:
            # notif
            await query.edit_message_text(
                "No hay estudiantes en el aula\n\n"
                "Elija una opción:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return states.EDIT_CLASSROOM_CHOOSE_OPTION

    elif option == "option_remove_teachers":
        # check if teacher is owner of the course
        if teacher.id == course.teacher_id:
            # show teachers in the classroom to remove
            teacher_ids = teacher_classroom_sql.get_teacher_ids(teacher.active_classroom_id)
            # remove user from the list
            teacher_ids.remove(teacher.id)
            if teacher_ids:
                buttons = [InlineKeyboardButton(f"{i}. {user_sql.get_user(teacher_id).fullname}", callback_data=f"remove_teacher#{teacher_id}") for i, teacher_id in enumerate(teacher_ids, start=1)]
                await query.edit_message_text(
                    "Elige un profesor:",
                    reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
                )
                return states.EDIT_CLASSROOM_REMOVE_TEACHER
            else:
                # notif
                await query.edit_message_text(
                    "No hay profesores en el aula\n\n"
                    "Elija una opción:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return states.EDIT_CLASSROOM_CHOOSE_OPTION
        else:
            await query.edit_message_text(
                "No puedes eliminar profesores de este curso\n\n"
                "Elija una opción:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return states.EDIT_CLASSROOM_CHOOSE_OPTION
        
    elif option == "option_delete_classroom":
        # check if teacher is owner of the course
        if teacher.id == course.teacher_id:
            await query.edit_message_text(
            "¿Estás seguro que deseas eliminar el aula?\n"
            "Esta acción no se puede deshacer, perderá toda la información"
            "asociada al aula.\n\n",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Eliminar", callback_data="delete_classroom_confirm")], [InlineKeyboardButton("Atrás", callback_data="option_edit_classroom_back")]]),
            )
            return states.EDIT_CLASSROOM_DELETE_CONFIRM
        else:
            await query.edit_message_text(
                "No puedes eliminar esta aula\n\n"
                "Elija una opción:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return states.EDIT_CLASSROOM_CHOOSE_OPTION

    elif option == "option_edit_classroom_back":
        # back to settings menu
        await query.message.reply_text(
            "Elija una opción:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_SETTINGS, one_time_keyboard=True, resize_keyboard=True),
        )

        # clear context.user_data["edit_classroom"] if exists
        if "edit_classroom" in context.user_data:
            context.user_data.pop("edit_classroom")
        
        return ConversationHandler.END
    
async def edit_classroom_name(update: Update, context: ContextTypes):
    # get name
    name = update.message.text
    # get classroom id
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.message.chat_id).id)
    classroom_id = teacher.active_classroom_id
    # update classroom name
    classroom_sql.update_classroom_name(classroom_id, name)
    # get classroom
    classroom = classroom_sql.get_classroom(classroom_id)

    course = course_sql.get_course(classroom.course_id)
    keyboard = keyboards.TEACHER_EDIT_CLASSROOM_OWNER if teacher.id == course.teacher_id else keyboards.TEACHER_EDIT_CLASSROOM
    # notif
    await update.message.reply_text(
        f"Nombre cambiado a {classroom.name}\n\n"
        "Elija una opcion:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return states.EDIT_COURSE_CHOOSE_OPTION

async def edit_classroom_password(update: Update, context: ContextTypes):
    # get password
    password = update.message.text
    # get classroom id
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.message.chat_id).id)
    classroom_id = teacher.active_classroom_id
    # get password type
    password_type = context.user_data["edit_classroom"]["password_type"]
    # update classroom password
    classroom_sql.update_classroom_password(classroom_id, password, password_type)
    # get classroom
    classroom = classroom_sql.get_classroom(classroom_id)

    course = course_sql.get_course(classroom.course_id)
    keyboard = keyboards.TEACHER_EDIT_CLASSROOM_OWNER if teacher.id == course.teacher_id else keyboards.TEACHER_EDIT_CLASSROOM
    # notif
    await update.message.reply_text(
        f"Contraseña cambiada\n\n"
        "Elija una opcion:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return states.EDIT_COURSE_CHOOSE_OPTION

async def edit_classroom_change(update: Update, context: ContextTypes):
    """ Selects a classroom to change to """
    query = update.callback_query
    query.answer()

    classroom_id = int(query.data.split("#")[1])
    # change active classroom
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.callback_query.message.chat_id).id)
    teacher_sql.set_teacher_active_classroom(teacher.id, classroom_id)

    classroom = classroom_sql.get_classroom(classroom_id)
    course = course_sql.get_course(classroom.course_id)
    keyboard = keyboards.TEACHER_EDIT_CLASSROOM_OWNER if teacher.id == course.teacher_id else keyboards.TEACHER_EDIT_CLASSROOM

    await query.edit_message_text(
        f"Aula: {classroom.name}\n"
        "Elige una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return states.EDIT_CLASSROOM_CHOOSE_OPTION

async def edit_classroom_remove_student(update: Update, context: ContextTypes):
    """ Removes the selected student from the classroom.
    Does not deletes the student from the database, only the association"""
    query = update.callback_query
    query.answer()

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.callback_query.message.chat_id).id)

    student_id = int(query.data.split("#")[1])
    # check if student's active classroom is the current one and if so set it to None
    student = student_sql.get_student(student_id)
    if student.active_classroom_id == teacher.active_classroom_id:
        student_sql.set_student_active_classroom(student_id, None)
        logger.info(f"Student {student_id} active classroom set to None when removed from classroom {teacher.active_classroom_id}")
    # remove student from classroom
    student_classroom_sql.remove_student(student_id, teacher.active_classroom_id)
    
    classroom = classroom_sql.get_classroom(teacher.active_classroom_id)
    course = course_sql.get_course(classroom.course_id)
    keyboard = keyboards.TEACHER_EDIT_CLASSROOM_OWNER if teacher.id == course.teacher_id else keyboards.TEACHER_EDIT_CLASSROOM
  
    await query.edit_message_text(
        f"Estudiante removido\n\n"
        "Elija una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return states.EDIT_CLASSROOM_CHOOSE_OPTION

async def edit_classroom_remove_teacher(update: Update, context: ContextTypes):
    """ Removes the selected teacher from the classroom.
    Does not deletes the teacher from the database, only the association"""
    query = update.callback_query
    query.answer()

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.callback_query.message.chat_id).id)
    teacher_to_id = int(query.data.split("#")[1])   
    # check if teacher's active classroom is the current one and if so set it to None
    teacher_to = teacher_sql.get_teacher(teacher_to_id)
    if teacher_to.active_classroom_id == teacher.active_classroom_id:
        teacher_sql.set_teacher_active_classroom(teacher_to_id, None)
        logger.info(f"Teacher {teacher_to_id} active classroom set to None when removed from classroom {teacher.active_classroom_id}")
    # remove teacher from classroom
    teacher_classroom_sql.remove_teacher(teacher_to_id, teacher.active_classroom_id)
  
    await query.edit_message_text(
        f"Profesor removido\n\n"
        "Elija una opción:",
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_EDIT_CLASSROOM_OWNER)
    )
    return states.EDIT_CLASSROOM_CHOOSE_OPTION

async def edit_classroom_delete(update: Update, context: ContextTypes):
    """ If user confirms, remove classroom from db"""
    query = update.callback_query
    query.answer()

    # first set to none the active classroom of the teachers (including this one)
    # and students in this classroom.
    classroom_id = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.callback_query.message.chat_id).id).active_classroom_id
    # get teachers in classroom
    teachers = teacher_sql.get_teachers_by_classroom(classroom_id)
    # get students in classroom
    students = student_sql.get_students_by_classroom(classroom_id)
    # set active classroom to None
    for teacher in teachers:
        teacher_sql.set_teacher_active_classroom(teacher.id, None)
    for student in students:
        student_sql.set_student_active_classroom(student.id, None)
    
    if query.data == "delete_classroom_confirm":
        # delete classroom
        classroom_sql.delete_classroom(classroom_id)

        context.user_data.clear()
        await query.message.reply_text(
            "Aula eliminada",
            reply_markup=ReplyKeyboardMarkup([["/start"]], one_time_keyboard=True, resize_keyboard=True),
        )

        return ConversationHandler.END
    else:
        await query.edit_message_text(
            "Elige una opción:",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_EDIT_CLASSROOM_OWNER)
        )
        return states.EDIT_CLASSROOM_CHOOSE_OPTION

async def edit_classroom_back(update: Update, context: ContextTypes):
    """Returns to settings menu"""
    query = update.callback_query
    query.answer()

    await query.message.reply_text(
        "Elija una opción:",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_SETTINGS, one_time_keyboard=True, resize_keyboard=True),
    )

    # clear context.user_data["edit_classroom"] if exists
    if "edit_classroom" in context.user_data:
        context.user_data.pop("edit_classroom")

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

edit_classroom_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Editar aula$"), edit_classroom)],
    states={
        states.EDIT_CLASSROOM_CHOOSE_OPTION: [CallbackQueryHandler(edit_classroom_choose_option, pattern=r"^option_")],
        states.EDIT_CLASSROOM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_classroom_name)],
        states.EDIT_CLASSROOM_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_classroom_password)],
        states.EDIT_CLASSROOM_CHANGE: [
            CallbackQueryHandler(edit_classroom_change, pattern=r"^change_classroom"),
            paginator_handler
            ],
        states.EDIT_CLASSROOM_REMOVE_STUDENT: [
            CallbackQueryHandler(edit_classroom_remove_student, pattern=r"^remove_student"),
            paginator_handler
            ],
        states.EDIT_CLASSROOM_REMOVE_TEACHER: [
            CallbackQueryHandler(edit_classroom_remove_teacher, pattern=r"^remove_teacher"),
            paginator_handler
            ],
        states.EDIT_CLASSROOM_DELETE_CONFIRM: [CallbackQueryHandler(edit_classroom_delete, pattern=r"^delete_classroom_confirm")],
    },
    fallbacks=[
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu),
        CallbackQueryHandler(edit_classroom_back, pattern=r"^(option_edit_classroom_back|back)$"),
    ]
)
