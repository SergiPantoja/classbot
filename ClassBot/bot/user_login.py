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
from sql import (
    user_sql, student_sql, teacher_sql, course_sql, classroom_sql, student_classroom_sql,
    teacher_classroom_sql
)
from bot.utils import states, keyboards
from bot.utils.inline_keyboard_pagination import paginator, paginated_keyboard, paginator_handler


# Start command, initiates user login conversation
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # clear user data
    context.user_data.clear()

    # Check if user with this chatid exists
    user = user_sql.get_user_by_chatid(update.effective_chat.id)
    
    if user:    # user exists, ask to login as student or teacher
        logger.info("User exists, asking for login...")
        await update.message.reply_text(
            f"Hola {user.fullname}! Seleccione su rol:",
            reply_markup=ReplyKeyboardMarkup(keyboards.SELECT_ROLE, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Eres profesor o estudiante?"),
        )
        return states.ROLE_SELECTED  # goes to user login convo
    else:       # ask for fullname to create new user
        logger.info("New user detected, asking for fullname...")
        await update.message.reply_text(
            "Hola! Soy senyor bigotes, su asistente de clases personal.\n\n"
            "Para comenzar, por favor ingrese su nombre completo:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return states.NEW_USER  # goes to user login convo


async def new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get fullname from user
    fullname = update.message.text

    # save fullname to context
    context.user_data["fullname"] = fullname

    # ask if its correct
    await update.message.reply_text(
        f"Gracias {fullname}! Si es correcto, proceda a crear su cuenta.",
        reply_markup=ReplyKeyboardMarkup(keyboards.NEW_USER, one_time_keyboard=True, resize_keyboard=True),
    )
    return states.USER_ROLE

async def select_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # if is a new user, first add it to the db
    if not user_sql.get_user_by_chatid(update.effective_chat.id):
        user_sql.add_user(update.effective_chat.id, context.user_data["fullname"])
        logger.info("New user %s created.\n\n", context.user_data["fullname"])
    # Show the representation of the user in the db
    logger.info("User %s", user_sql.get_user_by_chatid(update.effective_chat.id))
    # then, ask for role
    await update.message.reply_text(
        "Seleccione su rol:",
        reply_markup=ReplyKeyboardMarkup(keyboards.SELECT_ROLE, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Eres profesor o estudiante?"),
    )

    return states.ROLE_SELECTED

async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ If the user is a student, ask for the class code. If the user is a
    teacher, ask for either entering a class or creating a new class or course.
    If is first time loging in it inserts the corresponding rows in either student or teacher tables with
    the user_id since this are inherited tables from the user table."""
    logger.info("User %s selected role %s", update.message.from_user.first_name, update.message.text)
    if update.message.text == "Estudiante":
        # User is a student, check if it has an student account
        user_id = user_sql.get_user_by_chatid(update.effective_chat.id).id
        if not student_sql.get_student(user_id):
            # create student row in db
            student_sql.add_student(user_id)
            logger.info("New student added to db.\n\n")
        logger.info("Student %s", student_sql.get_student(user_id))
        # ask for class code
        await update.message.reply_text(
            "Ingrese el codigo de la clase:",
            reply_markup=ReplyKeyboardMarkup(keyboards.CANCEL, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.STUDENT_LOGIN
    
    elif update.message.text == "Profesor":
        # User is a teacher, check if it has a teacher account
        user_id = user_sql.get_user_by_chatid(update.effective_chat.id).id
        if not teacher_sql.get_teacher(user_id):
            # create teacher row in db
            teacher_sql.add_teacher(user_id)
            logger.info("New teacher added to db.\n\n")
        logger.info("Teacher %s", teacher_sql.get_teacher(user_id))
        # asks to either login to an existing classroom or create a new one/course
        await update.message.reply_text(
            "Seleccione una opcion:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_LOGIN, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.TEACHER_LOGIN
    else:
        # unexpected input
        await update.message.reply_text(
            "No entiendo. Por favor seleccione una opcion:",
            reply_markup=ReplyKeyboardMarkup(keyboards.SELECT_ROLE, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Eres profesor o estudiante?"),
        )
        return states.ROLE_SELECTED
    
async def student_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Receives the classroom code and checks if it is valid. If it is, it
    creates the corresponding row in student_classroom using student_id and
    classroom_id. Then sets the active classroom of the student to the joined
    classroom (logs him in). Ends showing the student main menu and the clasroom
    info."""
    # get student_auth from input
    student_auth = update.message.text
    # check if classroom exists
    classroom = classroom_sql.get_classroom_by_student_auth(student_auth)
    if classroom:
        # get student_id
        student_id = user_sql.get_user_by_chatid(update.effective_chat.id).id
        # create student_classroom in db if not exists
        if not student_classroom_sql.exists(student_id, classroom.id):
            student_classroom_sql.add_student_classroom(student_id, classroom.id)
            logger.info("New student_classroom added to db.\n\n")
        else:
            logger.info("Student_classroom already exists.\n\n")
        # set active classroom of student to this classroom
        student_sql.set_student_active_classroom(student_id, classroom.id)
        logger.info("Student %s logged in to classroom %s.\n\n", update.message.from_user.first_name, classroom.name)

        # add user role to context
        context.user_data["role"] = "student"

        # show student main menu and classroom info
        await update.message.reply_text(
            f"Bienvenido {user_sql.get_user_by_chatid(update.effective_chat.id).fullname}!\n\n"
            f"Curso: {course_sql.get_course(classroom.course_id).name}\n"
            f"Aula: {classroom.name}\n"
            f"menu en construccion...",
            reply_markup=ReplyKeyboardMarkup(keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )

        return ConversationHandler.END
    else:
        # classroom does not exist
        await update.message.reply_text(
            "El aula enviada no existe. Por favor ingrese un aula existente:",
            reply_markup=ReplyKeyboardMarkup(keyboards.CANCEL, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.STUDENT_LOGIN
    
async def teacher_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ asks for the class code to login to a classroom or to create a new classroom or course"""
    if update.message.text == "Ingresar al aula":
        logger.info("Teacher %s selected to login to a classroom.", update.message.from_user.first_name)
        # ask for class code
        await update.message.reply_text(
            "Ingrese el codigo de la clase:",
            reply_markup=ReplyKeyboardMarkup(keyboards.CANCEL, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.TEACHER_ENTER
    elif update.message.text == "Crear":
        logger.info("Teacher %s selected to create a classroom or course.", update.message.from_user.first_name)
        await update.message.reply_text(
            "Seleccione una opcion:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_CREATE, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.TEACHER_CREATE
    else:
        # unexpected input
        await update.message.reply_text(
            "No entiendo. Por favor seleccione una opcion:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_LOGIN, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.TEACHER_LOGIN
    
async def teacher_enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Receives the classroom code and checks if it is valid. If it is, it
    creates the corresponding row in teacher_classroom using teacher_id and
    classroom_id. Then sets the active classroom of the teacher to the joined
    classroom (logs him in). Ends showing the teacher main menu and the clasroom
    info."""
    # get teacher_auth from input
    teacher_auth = update.message.text
    # check if classroom exists
    classroom = classroom_sql.get_classroom_by_teacher_auth(teacher_auth)
    if classroom:
        # get teacher_id
        teacher_id = user_sql.get_user_by_chatid(update.effective_chat.id).id
        # create teacher_classroom in db if not exists
        if not teacher_classroom_sql.exists(teacher_id, classroom.id):
            teacher_classroom_sql.add_teacher_classroom(teacher_id, classroom.id)
            logger.info("New teacher_classroom added to db.\n\n")
        else:
            logger.info("Teacher_classroom already exists.\n\n")
        # set active classroom of teacher to this classroom
        teacher_sql.set_teacher_active_classroom(teacher_id, classroom.id)
        logger.info("Teacher %s logged in to classroom %s.\n\n", update.message.from_user.first_name, classroom.name)

        # add user role to context
        context.user_data["role"] = "teacher"

        # show teacher main menu and classroom info
        await update.message.reply_text(
            f"Bienvenido profe {user_sql.get_user_by_chatid(update.effective_chat.id).fullname}!\n\n"
            f"Curso: {course_sql.get_course(classroom.course_id).name}\n"
            f"Aula: {classroom.name}\n"
            f"menu en construccion...",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )

        return ConversationHandler.END
    else:
        # classroom does not exist
        await update.message.reply_text(
            "El aula enviada no existe. Por favor ingrese un aula existente o cree una:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_LOGIN, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.TEACHER_LOGIN
    
async def teacher_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ It allows for the creation of a new classroom or course by the teacher.
    If course was selected previously, it asks for the course name. If classroom
    was selected instead, it will show all courses 'belonging' to the teacher 
    and ask for the course to create the classroom in. If there are no courses,
    returns to this state asking to create a course first"""
    if update.message.text == "Crear curso":
        logger.info("Teacher %s selected to create a course.", update.message.from_user.first_name)
        await update.message.reply_text(
            "Ingrese el nombre del curso:",
            reply_markup=ReplyKeyboardMarkup(keyboards.CANCEL, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.NEW_COURSE
    elif update.message.text == "Crear aula":
        logger.info("Teacher %s selected to create a classroom.", update.message.from_user.first_name)
        # get teacher_id
        teacher_id = user_sql.get_user_by_chatid(update.effective_chat.id).id
        # get courses for this teacher
        courses = course_sql.get_courses_by_teacher(teacher_id)
        if courses:
            # show courses and ask for course to create classroom in. Use
            # inline keyboard and callback data to save course_id to context
            buttons = [InlineKeyboardButton(f"{i}. {course.name}", callback_data=f"COURSE#{course.id}") for i, course in enumerate(courses, start=1)]
            
            await update.message.reply_text(
                "Seleccione el curso en el que desea crear el aula:",
                reply_markup=paginated_keyboard(buttons, context=context),
            )
            return states.SELECT_COURSE
        else:
            # no courses, ask to create a course first
            await update.message.reply_text(
                "No tiene cursos creados. Por favor cree un curso primero.",
                reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_CREATE, one_time_keyboard=True, resize_keyboard=True),
            )
            return states.TEACHER_CREATE
    else:
        # unexpected input
        await update.message.reply_text(
            "No entiendo. Por favor seleccione una opcion:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_CREATE, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.TEACHER_CREATE
    
async def new_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Receives the course name and creates a new course assigning the teacher_id
    of the creator. Returns to TEACHER_CREATE state (for creating a classroom). """
    course_name = update.message.text
    teacher_id = user_sql.get_user_by_chatid(update.effective_chat.id).id # teacher_id is the same as its parent user_id
    # create course in db
    course_sql.add_course(teacher_id, course_name)
    logger.info("New course added to db.\n\n")
    # return to TEACHER_CREATE state
    await update.message.reply_text(
        "Curso creado! Seleccione una opcion:",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_CREATE, one_time_keyboard=True, resize_keyboard=True),
    )
    return states.TEACHER_CREATE

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Receives the course id space separated from the course name entered as 
    a button. Checks if the course exists and saves the course_id to context.
    Then asks for classroom name, teacher auth and student auth."""
    query = update.callback_query
    await query.answer()

    try:
        # get course id from callback data
        course_id = int(query.data.split("#")[1])
        # check if course exists
        course = course_sql.get_course(course_id)
    except:
        # unexpected input
        await query.message.reply_text(
            "No entiendo. Por favor seleccione una opcion:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_CREATE, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.TEACHER_CREATE
    if course:
        # check if course belongs to teacher (should always be true but if a user
        # knows the id of a course that does not belong to him, he could create
        # a classroom in it)
        teacher_id = user_sql.get_user_by_chatid(update.effective_chat.id).id
        if course.teacher_id != teacher_id:
            # course does not belong to teacher
            await query.message.reply_text(
                "No posee autorización para crear un aula de este curso. Por favor seleccione un curso existente o cree uno:",
                reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_CREATE, one_time_keyboard=True, resize_keyboard=True),
            )
            return states.TEACHER_CREATE
        # save course_id to context
        context.user_data["course_id"] = course_id
        # ask for classroom name, teacher auth and student auth (in that order)
        # separated by spaces
        await query.message.reply_text(
            "Ingrese el nombre del aula, la contraseña de profesor y la contraseña de estudiante separados por espacios en ese orden.",
            reply_markup=ReplyKeyboardMarkup(keyboards.CANCEL, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.NEW_CLASSROOM
    else:
        # course does not exist
        await query.message.reply_text(
            "El curso enviado no existe. Por favor seleccione un curso existente o cree uno:",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_CREATE, one_time_keyboard=True, resize_keyboard=True),
        )
        return states.TEACHER_CREATE

async def new_classroom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Receives the classroom name, teacher auth and student auth space separated
    by spaces and using the already saved course_id in context, creates a new
    classroom in the database. Then creates the corresponding row in teacher_classroom
    using teacher_id and classroom_id. Ends showing the teacher main menu and the
    clasroom info. Sets the active classroom of the teacher to the created classroom 
    (logs him in)."""
    try:
        # get classroom name, teacher auth and student auth from input
        classroom_name, teacher_auth, student_auth = update.message.text.split()
        # get teacher_id
        teacher_id = user_sql.get_user_by_chatid(update.effective_chat.id).id
        # get course_id from context
        course_id = context.user_data["course_id"]
        # create classroom in db
        classroom_sql.add_classroom(course_id, classroom_name, teacher_auth, student_auth)
        logger.info("New classroom added to db.\n\n")
        # get classroom_id
        classroom_id = classroom_sql.get_classroom_by_teacher_auth(teacher_auth).id
        # create teacher_classroom in db if not exists
        if not teacher_classroom_sql.exists(teacher_id, classroom_id):
            teacher_classroom_sql.add_teacher_classroom(teacher_id, classroom_id)
            logger.info("New teacher_classroom added to db.\n\n")
        else:
            logger.info("Teacher_classroom already exists.\n\n")
        # set active classroom of teacher to this classroom
        teacher_sql.set_teacher_active_classroom(teacher_id, classroom_id)
        logger.info("Teacher %s logged in to classroom %s.\n\n", update.message.from_user.first_name, classroom_name)

        # add user role to context
        context.user_data["role"] = "teacher"

        # show teacher main menu and classroom info
        await update.message.reply_text(
            f"Bienvenido profe {user_sql.get_user_by_chatid(update.effective_chat.id).fullname}!\n\n"
            f"Curso: {course_sql.get_course(course_id).name}\n"
            f"Aula: {classroom_name}\n"
            f"menu en construccion...",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )

        return ConversationHandler.END
    except Exception as e:
        # if error is because the auth is already in use, since it is unique in
        # the db, notify the user

        if "UNIQUE constraint failed" in str(e):
            await update.message.reply_text(
                "*La contraseña de profesor o estudiante ya esta en uso. Por favor ingrese una contraseña diferente:",
                reply_markup=ReplyKeyboardMarkup(keyboards.CANCEL, one_time_keyboard=True, resize_keyboard=True),
            )
        else:
            # unexpected input
            await update.message.reply_text(
                "No entiendo. Por favor ingrese el nombre del aula, la contraseña de profesor y la contraseña de estudiante separados por espacios en ese orden:",
                reply_markup=ReplyKeyboardMarkup(keyboards.CANCEL, one_time_keyboard=True, resize_keyboard=True),
            )
        return states.NEW_CLASSROOM


async def cancel_user_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """cancels the log in process. returns to initial state of the bot.
    Changes already made are not reverted. For example if the user already
    created an account, it will remain in the database. If the user as teacher
    already created a class or course, it will remain in the database.
    """
    logger.info("User %s canceled the login process.", update.message.from_user.first_name)

    # clear user data
    context.user_data.clear()

    await update.message.reply_text(
        "ok :( presione start si cambia de opinion.",
        reply_markup=ReplyKeyboardMarkup(
            [["/start"]], resize_keyboard=True
        ),
    )

    return ConversationHandler.END


# Handlers
start_handler = CommandHandler("start", start)
user_login_conv = ConversationHandler(
    entry_points=[start_handler],
    states={
        states.NEW_USER: [ MessageHandler(filters.TEXT & ~filters.COMMAND, new_user)],
        states.USER_ROLE: [ MessageHandler(filters.TEXT & ~filters.COMMAND, select_role)],
        states.ROLE_SELECTED: [ MessageHandler(filters.TEXT & ~filters.COMMAND, role_selected)],
        states.TEACHER_LOGIN: [ MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_login)],
        states.TEACHER_CREATE: [ MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_creation)],
        states.NEW_COURSE: [ MessageHandler(filters.TEXT & ~filters.COMMAND, new_course)],
        states.SELECT_COURSE: [ 
            CallbackQueryHandler(select_course, pattern="^COURSE#"),
            paginator_handler,
            ],
        states.NEW_CLASSROOM: [ MessageHandler(filters.TEXT & ~filters.COMMAND, new_classroom)],
        states.STUDENT_LOGIN: [ MessageHandler(filters.TEXT & ~filters.COMMAND, student_login)],
        states.TEACHER_ENTER: [ MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_enter)],
    },
    fallbacks=[CommandHandler("cancel", cancel_user_login)],
)
