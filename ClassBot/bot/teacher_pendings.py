import datetime

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    filters,
)

from utils.logger import logger
from bot.utils import states, keyboards
from bot.utils.inline_keyboard_pagination import paginated_keyboard, paginator_handler
from bot.utils.pagination import Paginator, text_paginator_handler
from sql import user_sql, teacher_sql, classroom_sql, course_sql, conference_sql, pending_sql, token_type_sql, student_sql, teacher_classroom_sql
from bot.teacher_settings import back_to_teacher_menu


async def teacher_pendings(update: Update, context: ContextTypes):
    """ Shows the pendings of the current classroom, except direct pendings.
    Shows options for filtering by pending type (token_type) or showing direct pendings.
    Enters the pendings conversation handler."""
    # In case it is a callback query, like when returning from direct pendings
    query = update.callback_query
    if query:
        query.answer()
    
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
    # get the list of pendings of this classroom that are "PENDING" and not direct pendings
    pendings = pending_sql.get_pendings_by_classroom(classroom_id, status="PENDING")
    
    if pendings:
        # create a list of lines for each pending
        lines = [f"{i}. {token_type_sql.get_token_type(pending.token_type_id).type}: {user_sql.get_user(pending.student_id).fullname} Fecha: {datetime.date(pending.creation_date.year, pending.creation_date.month, pending.creation_date.day)} -> /pending_{pending.id} {'(Esperando más información)' if pending.more_info == 'PENDING' else ''}{'(Nueva información recibida)' if pending.more_info == 'SENT' else ''}" for i, pending in enumerate(pendings, start=1)]
        # create new paginator using this lines
        other_buttons = [InlineKeyboardButton("Mis pendientes", callback_data="direct_pendings"), InlineKeyboardButton("Filtrar", callback_data="filter_pendings")]
        paginator = Paginator(lines, items_per_page=10, text_before="Pendientes del aula:", add_back=True, other_buttons=other_buttons)
        # save paginator in user_data
        context.user_data["paginator"] = paginator
        # send first page
        if query:
            await query.edit_message_text(
                paginator.text(),
                reply_markup=paginator.keyboard()
            )
        else:
            await update.message.reply_text(
                paginator.text(),
                reply_markup=paginator.keyboard()
            )
        return states.T_PENDING_SELECT

    else:   # no pendings in the classroom
        # check if teacher has direct pendings and show those instead, if not
        # return to teacher menu
        direct_pendings = pending_sql.get_direct_pendings_of_teacher(teacher.id, classroom_id, status="PENDING")
        if direct_pendings:
            # create a list of lines for each pending
            lines = [f"{i}. {token_type_sql.get_token_type(pending.token_type_id).type}: {user_sql.get_user(pending.student_id).fullname} Fecha: {datetime.date(pending.creation_date.year, pending.creation_date.month, pending.creation_date.day)} -> /pending_{pending.id} {'(Esperando más información)' if pending.more_info == 'PENDING' else ''}{'(Nueva información recibida)' if pending.more_info == 'SENT' else ''}" for i, pending in enumerate(direct_pendings, start=1)]
            # create new paginator using this lines
            other_buttons = [InlineKeyboardButton("Todos los pendientes", callback_data="all_pendings"), InlineKeyboardButton("Filtrar", callback_data="filter_pendings")]
            paginator = Paginator(lines, items_per_page=10, text_before="Aquí están tus pendientes directos, no hay más pendientes en el aula:", add_back=True, other_buttons=other_buttons)
            # save paginator in user_data
            context.user_data["paginator"] = paginator
            # send first page
            if query:
                await query.edit_message_text(
                    paginator.text(),
                    reply_markup=paginator.keyboard()
                )
            else:
                await update.message.reply_text(
                    paginator.text(),
                    reply_markup=paginator.keyboard()
                )
            return states.T_PENDING_SELECT
        else:
            if query:
                await query.message.reply_text(
                    "No hay pendientes en este momento.",
                    reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
                )
            else:
                await update.message.reply_text(
                "No hay pendientes en este momento.",
                reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
            )
            return ConversationHandler.END

async def teacher_direct_pendings(update: Update, context: ContextTypes):
    """ Shows only the direct pendings of the current teacher in the current classroom."""
    query = update.callback_query
    query.answer()

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    # get the list of direct pendings of this classroom that are "PENDING"
    pendings = pending_sql.get_direct_pendings_of_teacher(teacher.id, classroom_id, status="PENDING")
    
    if pendings:
        # create a list of lines for each pending
        lines = [f"{i}. {token_type_sql.get_token_type(pending.token_type_id).type}: {user_sql.get_user(pending.student_id).fullname} Fecha: {datetime.date(pending.creation_date.year, pending.creation_date.month, pending.creation_date.day)} -> /pending_{pending.id} {'(Esperando más información)' if pending.more_info == 'PENDING' else ''}{'(Nueva información recibida)' if pending.more_info == 'SENT' else ''}" for i, pending in enumerate(pendings, start=1)]
        # create new paginator using this lines
        other_buttons = [InlineKeyboardButton("Todos los pendientes", callback_data="all_pendings"), InlineKeyboardButton("Filtrar", callback_data="filter_pendings")]
        paginator = Paginator(lines, items_per_page=10, text_before="Mis pendientes directos:", add_back=True, other_buttons=other_buttons)
        # save paginator in user_data
        context.user_data["paginator"] = paginator
        # send first page
        await query.edit_message_text(
            paginator.text(),
            reply_markup=paginator.keyboard()
        )
        return states.T_PENDING_SELECT

    else:   # no pendings, return to teacher main menu
        await query.message.reply_text(
            "No tienes pendientes directos en este momento.",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
        return ConversationHandler.END

async def pending_info(update: Update, context: ContextTypes):
    """ Shows information of the selected pending.
    Shows options for approving or rejecting it, or alternatively marking it as
    a direct pending."""
    logger.info("pending_info")
    try:
        pending_id = int(update.message.text.split("_")[1])
        # save pending_id in user_data
        if not "pending" in context.user_data:
            context.user_data["pending"] = {"id": pending_id}
        else:
            context.user_data["pending"]["id"] = pending_id
    except:
        await update.message.reply_text(
            "No entiendo el comando, por favor intenta de nuevo.",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
    
    pending = pending_sql.get_pending(pending_id)
    student_name = user_sql.get_user(pending.student_id).fullname
    token_type = token_type_sql.get_token_type(pending.token_type_id).type
    creation_date = datetime.date(pending.creation_date.year, pending.creation_date.month, pending.creation_date.day)

    text = f"{token_type} de {student_name} el {creation_date}:\n\n"

    #if pending.guild_id:
        #guild_name = guild_sql.get_guild(pending.guild_id).name
        #text = text.rstrip("\n")
        #text += f"\nGremio: {guild_name}\n\n"
    if pending.status == "APPROVED":
        approved_by = user_sql.get_user(pending.approved_by).fullname
        approved_date = datetime.date(pending.approved_date.year, pending.approved_date.month, pending.approved_date.day)
        text += f"Estado: APROBADO\n"
        text += f"Aprobado por: {approved_by}\n"
        text += f"Fecha de aprobación: {approved_date}\n\n"
    elif pending.teacher_id:
        teacher_name = user_sql.get_user(teacher_sql.get_teacher(pending.teacher_id).id).fullname
        text = text.rstrip("\n")
        text += f"\nProfesor: {teacher_name}.\n"
    if pending.text:
        text += f"Texto: {pending.text}\n"
    text += "\nSeleccione una opción:"

    if pending.FileID:
        try:
            try:
                await update.message.reply_photo(pending.FileID, caption=text)
            except BadRequest:
                await update.message.reply_document(pending.FileID, caption=text)
        except BadRequest:
            await update.message.reply_text(
                "Parece que el archivo no se encuentra disponible.\n Esto puede"
                "deberse a que el usuario lo haya eliminado pues estos archivos"
                "se guardan en la nube de Telegram. Puede pedirle al usuario que"
                "lo vuelva a enviar."
            )
    await update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PENDING_OPTIONS),
    )
    return states.T_PENDING_OPTIONS

async def manage_pending(update: Update, context: ContextTypes):
    """ Manages the selected pending according to the selected option."""
    query = update.callback_query
    query.answer()

    pending_id = context.user_data["pending"]["id"]
    pending = pending_sql.get_pending(pending_id)
    pending_type = token_type_sql.get_token_type(pending.token_type_id).type
    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)

    if query.data == "pending_approve":
        return ConversationHandler.END
    
    elif query.data == "pending_reject":
        # asks the teacher for an explanation (optional, reason for rejection)
        await query.edit_message_text(
            text=f"Puede ingresar una razón para el rechazo de {pending_type} de {user_sql.get_user(pending.student_id).fullname} o presione continuar. Se le notificará al estudiante.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="pending_reject_continue")], [InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.T_PENDING_REJECT

    elif query.data == "pending_assign":
        # get list of teachers of this classroom
        teacher_ids = teacher_classroom_sql.get_teacher_ids(teacher.active_classroom_id)
        if teacher_ids:
            buttons = [InlineKeyboardButton(f"{i}. {user_sql.get_user(teacher_id).fullname}", callback_data=f"assign#{teacher_id}") for i, teacher_id in enumerate(teacher_ids, start=1)]
            # shows the list of teachers to assing the pendign to.
            await query.edit_message_text(
                text="Seleccione un profesor para asignarle el pendiente:",
                reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
            )
            return states.T_PENDING_ASSIGN_TEACHER
        else:   # no teachers in this classroom
            old_text = query.message.text
            await query.edit_message_text(
                text=old_text + "\n\nNo hay otros profesores en este aula.",
                reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PENDING_OPTIONS),
            )
            return states.T_PENDING_OPTIONS

    elif query.data == "pending_ask_info":
        return ConversationHandler.END

async def assign_pending(update: Update, context: ContextTypes):
    """ Assigns the pending to the selected teacher as a direct pending.
    Returns to the teacher menu."""
    query = update.callback_query
    query.answer()

    pending_id = context.user_data["pending"]["id"]
    teacher_id = int(query.data.split("#")[1])
    teacher_name = user_sql.get_user(teacher_id).fullname
    pending_sql.assign_pending(pending_id, teacher_id)
    logger.info(f"Pending {pending_id} assigned to teacher {teacher_id}")
    
    await query.message.reply_text(
        text=f"El pendiente ha sido asignado a {teacher_name}.",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

async def reject_pending(update: Update, context: ContextTypes):
    """ Sets pending status to REJECTED and notifies the student."""
    query = update.callback_query
    if query:
        query.answer()
    
    pending_id = context.user_data["pending"]["id"]
    
    if query:
        pending_sql.reject_pending(pending_id)
        logger.info(f"Pending {pending_id} rejected")
        await query.message.reply_text(
            text="El pendiente ha sido rechazado.",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
    else:
        explanation = update.message.text
        pending_sql.reject_pending(pending_id, explanation)
        logger.info(f"Pending {pending_id} rejected")
        await update.message.reply_text(
            text="El pendiente ha sido rechazado.",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
    # notify student
    pending = pending_sql.get_pending(pending_id)
    student_chat_id = user_sql.get_user(pending.student_id).telegram_chatid
    student_name = user_sql.get_user(pending.student_id).fullname
    token_type = token_type_sql.get_token_type(pending.token_type_id).type
    pending_text = pending.text if pending.text else ""
    text = f"El profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} ha rechazado tu {token_type}.\n\nTu {token_type}:\n{pending_text}"
    if pending.explanation:
        text += f"\n\nRazón del rechazo:\n{pending.explanation}"
    try:
        await context.bot.send_message(
            chat_id=student_chat_id,
            text=text,
        )
    except BadRequest:
        logger.error(f"Error sending message to student {student_name} (chat_id: {student_chat_id})")
    return ConversationHandler.END



async def teacher_pendings_back(update: Update, context: ContextTypes):
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

    if "paginator" in context.user_data:
        context.user_data.pop("paginator")
    if "pending" in context.user_data:
        context.user_data.pop("pending")
    return ConversationHandler.END


# Handlers
teacher_pendings_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Pendientes$"), teacher_pendings)],
    states={
        states.T_PENDING_SELECT: [
            text_paginator_handler,
            CallbackQueryHandler(teacher_direct_pendings, pattern=r"^direct_pendings$"),
            CallbackQueryHandler(teacher_pendings, pattern=r"^all_pendings$"),
            #CallbackQueryHandler(teacher_pendings, pattern=r"^filter_pendings$"),
            MessageHandler(filters.TEXT & filters.Regex("^/pending_"), pending_info),
        ],
        states.T_PENDING_OPTIONS: [CallbackQueryHandler(manage_pending, pattern=r"^pending_")],
        states.T_PENDING_ASSIGN_TEACHER: [
            CallbackQueryHandler(assign_pending, pattern=r"^assign#"),
            paginator_handler,
            ],
        states.T_PENDING_REJECT: [
            CallbackQueryHandler(reject_pending, pattern=r"^pending_reject_continue$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reject_pending),
        ]
        
    },
    fallbacks=[
        CallbackQueryHandler(teacher_pendings_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
        ],
)
