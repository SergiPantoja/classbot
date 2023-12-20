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
from sql import user_sql, teacher_sql, classroom_sql, course_sql, pending_sql, token_type_sql, teacher_classroom_sql, token_sql, student_token_sql, guild_sql
from bot.teacher_settings import back_to_teacher_menu


async def teacher_pendings(update: Update, context: ContextTypes):
    """ Shows the pendings of the current classroom, except direct pendings.
    Shows options for filtering by pending type (token_type) or showing direct pendings.
    Enters the pendings conversation handler."""
    # Sanitize context.user_data
    clean_teacher_context(context)
    
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
    
    context.user_data["pending"] = {"direct": False, "history": False}

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    # get the list of pendings of this classroom that are "PENDING" and not direct pendings
    pendings = pending_sql.get_pendings_by_classroom(classroom_id, status="PENDING")
    
    if pendings:
        # create a list of lines for each pending
        lines = [f"{i}. {token_type_sql.get_token_type(pending.token_type_id).type}: {user_sql.get_user(pending.student_id).fullname} Fecha: {datetime.date(pending.creation_date.year, pending.creation_date.month, pending.creation_date.day)} -> /pending_{pending.id} {'(Esperando más información)' if pending.more_info == 'PENDING' else ''}{'(Nueva información recibida)' if pending.more_info == 'SENT' else ''}" for i, pending in enumerate(pendings, start=1)]
        # create new paginator using this lines
        other_buttons = [InlineKeyboardButton("Mis pendientes", callback_data="direct_pendings"), InlineKeyboardButton("Filtrar", callback_data="filter_pendings"), InlineKeyboardButton("Historial", callback_data="history_pendings")]
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
            other_buttons = [InlineKeyboardButton("Del aula", callback_data="all_pendings"), InlineKeyboardButton("Filtrar", callback_data="filter_pendings"), InlineKeyboardButton("Historial", callback_data="history_pendings")]
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

    if not "pending" in context.user_data:
        context.user_data["pending"] = {"direct": True}
    else:
        context.user_data["pending"]["direct"] = True

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    # get the list of direct pendings of this classroom that are "PENDING"
    pendings = pending_sql.get_direct_pendings_of_teacher(teacher.id, classroom_id, status="PENDING")
    
    if pendings:
        # create a list of lines for each pending
        lines = [f"{i}. {token_type_sql.get_token_type(pending.token_type_id).type}: {user_sql.get_user(pending.student_id).fullname} Fecha: {datetime.date(pending.creation_date.year, pending.creation_date.month, pending.creation_date.day)} -> /pending_{pending.id} {'(Esperando más información)' if pending.more_info == 'PENDING' else ''}{'(Nueva información recibida)' if pending.more_info == 'SENT' else ''}" for i, pending in enumerate(pendings, start=1)]
        # create new paginator using this lines
        other_buttons = [InlineKeyboardButton("Del aula", callback_data="all_pendings"), InlineKeyboardButton("Filtrar", callback_data="filter_pendings"), InlineKeyboardButton("Historial", callback_data="history_pendings")]
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

async def pending_history(update: Update, context: ContextTypes):
    """ Shows the history of previously approved pendings of the current classroom by the current teacher."""
    query = update.callback_query
    query.answer()

    # save in context teacher is viewing history
    if not "pending" in context.user_data:
        context.user_data["pending"] = {"history": True}
    else:
        context.user_data["pending"]["history"] = True

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id
    # get the list of pendings of this classroom that are "APPROVED" by this teacher
    pendings = pending_sql.get_approved_pendings_of_teacher(teacher.id, classroom_id)
    if pendings:
        lines = [f"{i}. {token_type_sql.get_token_type(pending.token_type_id).type}: {user_sql.get_user(pending.student_id).fullname} Aprobado el {datetime.date(pending.approved_date.year, pending.approved_date.month, pending.approved_date.day)} con un valor de {student_token_sql.get_value(pending.student_id, pending.token_id)} -> /pending_{pending.id}" for i, pending in enumerate(pendings, start=1)]
        # create new paginator using this lines
        other_buttons = [InlineKeyboardButton("Todos los pendientes", callback_data="all_pendings")]
        paginator = Paginator(lines, items_per_page=10, text_before="Historial de pendientes que has aprobado:", add_back=True, other_buttons=other_buttons)
        # save paginator in user_data
        context.user_data["paginator"] = paginator
        # send first page
        await query.edit_message_text(
            paginator.text(),
            reply_markup=paginator.keyboard()
        )
        return states.T_PENDING_SELECT
    else:
        await query.message.reply_text(
            "No has aprobado ningún pendiente en esta aula.",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
        return ConversationHandler.END

async def filter_pendings(update: Update, context: ContextTypes):
    """ Filter pendings by token type. Shows all default token types in the classroom
    and selecting one of them shows only the pendings of the classroom of that type.
    Selecting "Otras actividades" shows the pendings related to activities created
    by the teachers (token_types with classroom_id of this classroom)."""
    query = update.callback_query
    query.answer()

    teacher = teacher_sql.get_teacher(user_sql.get_user_by_chatid(update.effective_user.id).id)
    classroom_id = teacher.active_classroom_id

    if query.data == "filter_pendings":
        # show keyboard with default token types and "Otras actividades"
        await query.edit_message_text(
            text="Seleccione un tipo de pendiente para filtrar:",
            reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_FILTER_PENDING),
        )
        return states.T_PENDING_SELECT

    elif query.data == "filter_other_activities":
        # show keyboard with token types created by teachers
        pass

    # if query.data starts with "filter_default: " it means the teacher selected a default token type
    elif query.data.startswith("filter_default:"):
        # filter by default token type and show those
        t_type = query.data.split(":")[1]
        token_type_id = token_type_sql.get_token_type_by_type(t_type).id
        # get only pendings of this classroom with this token type
        if context.user_data["pending"]["direct"]:
            pendings = pending_sql.get_pendings_by_token_type(token_type_id, classroom_id, status="PENDING", direct_pending=teacher.id)
        else:
            pendings = pending_sql.get_pendings_by_token_type(token_type_id, classroom_id, status="PENDING")
            
        if pendings:
            # create a list of lines for each pending
            lines = [f"{i}. {token_type_sql.get_token_type(pending.token_type_id).type}: {user_sql.get_user(pending.student_id).fullname} Fecha: {datetime.date(pending.creation_date.year, pending.creation_date.month, pending.creation_date.day)} -> /pending_{pending.id} {'(Esperando más información)' if pending.more_info == 'PENDING' else ''}{'(Nueva información recibida)' if pending.more_info == 'SENT' else ''}" for i, pending in enumerate(pendings, start=1)]
            # create new paginator using this lines
            other_buttons = [InlineKeyboardButton("Todos los pendientes", callback_data="all_pendings"), InlineKeyboardButton("Filtrar", callback_data="filter_pendings"), InlineKeyboardButton("Historial", callback_data="history_pendings")]
            paginator = Paginator(lines, items_per_page=10, text_before=f'Pendientes de "{t_type}":', add_back=True, other_buttons=other_buttons)
            # save paginator in user_data
            context.user_data["paginator"] = paginator
            # send first page
            await query.edit_message_text(
                paginator.text(),
                reply_markup=paginator.keyboard()
            )
            return states.T_PENDING_SELECT
        else:
            await query.edit_message_text(
                text="No hay pendientes de este tipo.",
                reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_FILTER_PENDING),
            )
            return states.T_PENDING_SELECT

        
    #TODO: filter by created token types and show those

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

    if pending.guild_id:
        guild_name = guild_sql.get_guild(pending.guild_id).name
        text = text.rstrip("\n")
        text += f"\nGremio: {guild_name}\n\n"
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

    if context.user_data["pending"]["history"]:
        # if viewing history, only show options to return to history or back to menu
        if pending.FileID:
            try:
                try:
                    await update.message.reply_photo(
                        pending.FileID, 
                        caption=text,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Historial", callback_data="history_pendings")],[InlineKeyboardButton("Atrás", callback_data="back")]]),
                    )
                except BadRequest:
                    await update.message.reply_document(
                        pending.FileID,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Historial", callback_data="history_pendings")],[InlineKeyboardButton("Atrás", callback_data="back")]]),
                    )
            except BadRequest:
                await update.message.reply_text(
                    text=text + "\n\nSe ha producido un error al mostrar el archivo enviado con el pendiente. Es posible que haya sido eliminado.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Historial", callback_data="history_pendings")],[InlineKeyboardButton("Atrás", callback_data="back")]]),
                )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Historial", callback_data="history_pendings")],[InlineKeyboardButton("Atrás", callback_data="back")]]),
            )

    else: 
        # if not viewing history, show options to approve, reject or assign
        if pending.FileID:
            try:
                try:
                    await update.message.reply_photo(
                        pending.FileID, 
                        caption=text,
                        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PENDING_OPTIONS),
                    )
                except BadRequest:
                    await update.message.reply_document(
                        pending.FileID,
                        caption=text,
                        reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PENDING_OPTIONS),
                    )
            except BadRequest:
                await update.message.reply_text(
                    text=text + "\n\nSe ha producido un error al mostrar el archivo enviado con el pendiente. Es posible que haya sido eliminado.",
                    reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PENDING_OPTIONS),
                )
        else:
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
        # if pending is a diary update, check how many consecutive days in a row
        # the diary has been updated and give 10000 value multiplied by the total minutes

        if pending_type == "Actualización de diario":
            diary_updates = pending_sql.get_pendings_of_student_by_type(pending.student_id, teacher.active_classroom_id, token_type_sql.get_token_type_by_type("Actualización de diario").id)
            multiplier = 1
            current_pending_arrived = False
            # check how many consecutive days in a row the diary has been updated
            for i in range(len(diary_updates)-1):
                # start from the current pending in case there is newer ones that have not been approved yet or are rejected
                if diary_updates[i].id == pending_id:
                    current_pending_arrived = True
                if not current_pending_arrived:
                    continue
                if (diary_updates[i].creation_date - diary_updates[i+1].creation_date >= datetime.timedelta(days=1)) and (diary_updates[i].creation_date - diary_updates[i+1].creation_date <= datetime.timedelta(days=2)): 
                    # if one of these updates was rejected then break
                    if diary_updates[i].status == "REJECTED":
                        break
                    multiplier += 1
                else:
                    break
            value = 10000 * multiplier # later teacher can change this value in classroom settings
            # create token
            token_sql.add_token(name=f"{pending_type} de {user_sql.get_user(pending.student_id).fullname}", token_type_id=pending.token_type_id, classroom_id=teacher.active_classroom_id)
            logger.info(f"Token {pending_type} created")
            # update pending with this token
            pending_sql.update_token(pending_id, token_sql.get_last_token().id)

            # get token id
            token = pending_sql.get_token(pending_id)
            # assign token to student
            student_token_sql.add_student_token(student_id=pending.student_id, token_id=token.id, value=value, teacher_id=user_sql.get_user_by_chatid(update.effective_user.id).id)
            logger.info(f"Token {token.id} assigned to student {pending.student_id} with value {value}")
            # change pending status to approved
            pending_sql.approve_pending(pending_id, user_sql.get_user_by_chatid(update.effective_user.id).id)
            logger.info(f"Pending {pending_id} approved")

            # notify student
            text = f"El profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} ha aprobado tu {pending_type}.\n\nTu {pending_type}:\n{pending.text}"
            try:
                await context.bot.send_message(
                    chat_id=user_sql.get_user(pending.student_id).telegram_chatid,
                    text=text,
                )
            except BadRequest:
                logger.error(f"Error sending message to student {user_sql.get_user(pending.student_id).fullname} (chat_id: {user_sql.get_user(pending.student_id).telegram_chatid})")

            await query.message.reply_text(
                text="El pendiente ha sido aprobado.",
                reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
            )
            return ConversationHandler.END

        # Ask for value and comment, then create a token if it doesn't exist
        if query.message.text:
            await query.edit_message_text(
                f"Ingrese la cantidad de créditos a otorgar por el {pending_type} de {user_sql.get_user(pending.student_id).fullname}. Puede agregar un comentario después de la cantidad de créditos después de un espacio.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
            )
        else:
            await query.edit_message_caption(
                f"Ingrese la cantidad de créditos a otorgar por el {pending_type} de {user_sql.get_user(pending.student_id).fullname}. Puede agregar un comentario después de la cantidad de créditos después de un espacio.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
            )
        return states.T_PENDING_APPROVE
    
    elif query.data == "pending_reject":
        # asks the teacher for an explanation (optional, reason for rejection)
        if query.message.text:
            await query.edit_message_text(
                text=f"Puede ingresar una razón para el rechazo de {pending_type} de {user_sql.get_user(pending.student_id).fullname} o presione continuar. Se le notificará al estudiante.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Continuar", callback_data="pending_reject_continue")], [InlineKeyboardButton("Atrás", callback_data="back")]]),
            )
        else:
            await query.edit_message_caption(
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
            if query.message.text:
                await query.edit_message_text(
                    text="Seleccione un profesor para asignarle el pendiente:",
                    reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
                )
            else:
                await query.edit_message_caption(
                    text="Seleccione un profesor para asignarle el pendiente:",
                    reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
            )
            return states.T_PENDING_ASSIGN_TEACHER
        else:   # no teachers in this classroom
            if query.message.text:
                old_text = query.message.text
                await query.edit_message_text(
                    text=old_text + "\n\nNo hay otros profesores en este aula.",
                    reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PENDING_OPTIONS),
                )
            else:
                old_text = query.message.caption
                await query.edit_message_caption(
                    text=old_text + "\n\nNo hay otros profesores en este aula.",
                    reply_markup=InlineKeyboardMarkup(keyboards.TEACHER_PENDING_OPTIONS),
                )
            return states.T_PENDING_OPTIONS

    elif query.data == "pending_ask_info":
        # asks the teacher to send a message to the student asking for more information
        if query.message.text:
            await query.edit_message_text(
                text=f"Ingrese el mensaje que desea enviar al estudiante {user_sql.get_user(pending.student_id).fullname} para pedirle más información sobre el {pending_type}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
            )
        else:
            await query.edit_message_caption(
                text=f"Ingrese el mensaje que desea enviar al estudiante {user_sql.get_user(pending.student_id).fullname} para pedirle más información sobre el {pending_type}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Atrás", callback_data="back")]]),
        )
        return states.T_PENDING_MORE_INFO

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
            text="El pendiente ha sido denegado.",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
    else:
        explanation = update.message.text
        pending_sql.reject_pending(pending_id, explanation)
        logger.info(f"Pending {pending_id} rejected")
        await update.message.reply_text(
            text="El pendiente ha sido denegado. ",
            reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
        )
    # notify student
    pending = pending_sql.get_pending(pending_id)
    student_chat_id = user_sql.get_user(pending.student_id).telegram_chatid
    student_name = user_sql.get_user(pending.student_id).fullname
    token_type = token_type_sql.get_token_type(pending.token_type_id).type
    pending_text = pending.text if pending.text else ""
    text = f"El profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} ha denegado tu {token_type}.\n\nTu {token_type}:\n{pending_text}"
    if pending.explanation:
        text += f"\n\nRazón:\n{pending.explanation}"
    try:
        await context.bot.send_message(
            chat_id=student_chat_id,
            text=text,
        )
    except BadRequest:
        logger.error(f"Error sending message to student {student_name} (chat_id: {student_chat_id})")
    return ConversationHandler.END

async def approve_pending(update: Update, context: ContextTypes):
    """ Sets pending status to approved, creates the token and notifies the student."""
    query = update.callback_query
    if query:
        query.answer()

    pending_id = context.user_data["pending"]["id"]
    pending = pending_sql.get_pending(pending_id)
    student_chat_id = user_sql.get_user(pending.student_id).telegram_chatid
    student_name = user_sql.get_user(pending.student_id).fullname
    token_type = token_type_sql.get_token_type(pending.token_type_id).type
    classroom_id = pending.classroom_id

    text = update.message.text
    # get token value and comment
    try:
        value = int(text.split(" ")[0])
        comment = text.split(" ", 1)[1]
    except:
        value = int(text)
        comment = None
    
    token = pending_sql.get_token(pending_id)
    if not token:
        # create token
        token_sql.add_token(name=f"{token_type} de {student_name}", token_type_id=pending.token_type_id, classroom_id=classroom_id)
        logger.info(f"Token {token_type} created")
        # update pending with this token
        pending_sql.update_token(pending_id, token_sql.get_last_token().id)

    # get token id
    token = pending_sql.get_token(pending_id)
    # assign token to student
    student_token_sql.add_student_token(student_id=pending.student_id, token_id=token.id, value=value, teacher_id=user_sql.get_user_by_chatid(update.effective_user.id).id)
    logger.info(f"Token {token.id} assigned to student {pending.student_id} with value {value}")
    # change pending status to approved
    pending_sql.approve_pending(pending_id, user_sql.get_user_by_chatid(update.effective_user.id).id)
    logger.info(f"Pending {pending_id} approved")

    # notify student
    text = f"El profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} ha aprobado tu {token_type}.\n\nTu {token_type}:\n{pending.text}"
    if comment:
        text += f"\n\nComentario:\n{comment}"
    try:
        await context.bot.send_message(
            chat_id=student_chat_id,
            text=text,
        )
    except BadRequest:
        logger.error(f"Error sending message to student {student_name} (chat_id: {student_chat_id})")

    await update.message.reply_text(
        text="El pendiente ha sido aprobado.",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

async def more_info_pending(update: Update, context: ContextTypes):
    """ Updates the more_info field of the pending to PENDING, adds the message
    from the teacher to the pending text after a double line break and notifies
    the student."""

    pending_id = context.user_data["pending"]["id"]
    pending = pending_sql.get_pending(pending_id)
    student_chat_id = user_sql.get_user(pending.student_id).telegram_chatid
    student_name = user_sql.get_user(pending.student_id).fullname
    token_type = token_type_sql.get_token_type(pending.token_type_id).type
    teacher_chat_id = user_sql.get_user_by_chatid(update.effective_user.id).telegram_chatid

    # update pending
    text = f"> Pregunta de {user_sql.get_user_by_chatid(update.effective_user.id).fullname}:\n{update.message.text}"
    pending_sql.ask_for_more_info(pending_id, text)
    logger.info(f"Pending {pending_id} updated with more info from teacher")
    # notify student
    text = f"El profesor {user_sql.get_user_by_chatid(update.effective_user.id).fullname} ha solicitado más información sobre tu {token_type}.\n\nTu {token_type}:\n{pending_sql.get_pending(pending_id).text}"
    try:
        await context.bot.send_message(
            chat_id=student_chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Responder", callback_data=f"pending_more_info_student#{pending_id}#{teacher_chat_id}")]]),
        )
    except BadRequest:
        logger.error(f"Error sending message to student {student_name} (chat_id: {student_chat_id})")
    await update.message.reply_text(
        text="El mensaje ha sido enviado al estudiante.",
        reply_markup=ReplyKeyboardMarkup(keyboards.TEACHER_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True),
    )
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
            CallbackQueryHandler(filter_pendings, pattern=r"^filter_"),
            CallbackQueryHandler(pending_history, pattern=r"^history_pendings$"),
            MessageHandler(filters.TEXT & filters.Regex("^/pending_"), pending_info),
        ],
        states.T_PENDING_OPTIONS: [
            CallbackQueryHandler(manage_pending, pattern=r"^pending_"),
            CallbackQueryHandler(pending_history, pattern=r"^history_pendings$"),
            ],
        states.T_PENDING_ASSIGN_TEACHER: [
            CallbackQueryHandler(assign_pending, pattern=r"^assign#"),
            paginator_handler,
            ],
        states.T_PENDING_REJECT: [
            CallbackQueryHandler(reject_pending, pattern=r"^pending_reject_continue$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reject_pending),
        ],
        states.T_PENDING_APPROVE: [
            CallbackQueryHandler(approve_pending, pattern=r"^pending_approve_confirm$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, approve_pending),
        ],
        states.T_PENDING_MORE_INFO: [
            MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, more_info_pending),
        ],
        
    },
    fallbacks=[
        CallbackQueryHandler(teacher_pendings_back, pattern=r"^back$"),
        MessageHandler(filters.Regex("^Atrás$"), back_to_teacher_menu)
        ],
    allow_reentry=True,
)
