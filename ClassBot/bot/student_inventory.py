from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton
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
from bot.utils.clean_context import clean_student_context
from sql import user_sql, student_sql, student_token_sql, token_sql, classroom_sql, course_sql


async def student_inventory(update: Update, context: ContextTypes):
    """ Shows the student's inventory. """
    #sanitize context
    clean_student_context(context)
    
    # Check user role
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
   
    # get total credits of the student in this classroom
    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_chat.id).id)
    classroom_id = student.active_classroom_id
    total_credits = student_token_sql.get_total_value_by_classroom(student.id, classroom_id)
    
    await update.message.reply_text(
        f"Tienes {total_credits} créditos",
        reply_markup=ReplyKeyboardMarkup(
            keyboards.STUDENT_INVENTORY, one_time_keyboard=True, resize_keyboard=True
        ),
    )

async def back_to_student_menu(update: Update, context: ContextTypes):
    """ Returns to the student menu. """
    # if it is a query answer it 
    if update.callback_query:
        query = update.callback_query
        query.answer()
    
    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_chat.id).id)
    classroom_name = classroom_sql.get_classroom(student.active_classroom_id).name
    course_name = course_sql.get_course(classroom_sql.get_classroom(student.active_classroom_id).course_id).name

    await update.message.reply_text(
        f"Curso: {course_name}\nAula: {classroom_name}",
        reply_markup=ReplyKeyboardMarkup(
            keyboards.STUDENT_MAIN_MENU, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    
    #sanitize context
    clean_student_context(context)

    return ConversationHandler.END


# Medals conversation
async def show_medal_list(update: Update, context: ContextTypes):
    """ Shows a list of all the medals of this course this student has earned. """
    #sanitize context
    clean_student_context(context)
    
    # Check user role
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
    
    # get student
    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_chat.id).id)
    # get classroom
    classroom_id = student.active_classroom_id
    # get medals
    tokens = student_token_sql.get_tokens_by_student_and_classroom(student.id, classroom_id)
    medals = [token for token in tokens if token.token_type_id == 1] # 1 is the id of the medal token type

    if medals:
        buttons = [InlineKeyboardButton(f"{i}. {medal.name}", callback_data=f"medal#{medal.id}") for i, medal in enumerate(medals, start=1)]
        await update.message.reply_text(
            "Medallas:",
            reply_markup=paginated_keyboard(buttons, context=context, add_back=True),
        )
        return states.SI_SELECT_MEDAL
    else:
        await update.message.reply_text(
            "No tienes medallas",
            reply_markup=ReplyKeyboardMarkup(
                keyboards.STUDENT_INVENTORY, one_time_keyboard=True, resize_keyboard=True
            ),
        )
        return ConversationHandler.END

async def select_medal(update: Update, context: ContextTypes):
    """ Selects a medal to see its description. """
    query = update.callback_query
    query.answer()
    medal_id = int(query.data.split("#")[1])
    medal = token_sql.get_token(medal_id)

    # get image if any
    if medal.image_url:
        if "path" in medal.image_url:
            await query.message.reply_photo(
                open(medal.image_url.split(":")[1], "rb"),
                caption=f"{medal.name}\n{medal.description if medal.description else ''}",
                reply_markup=ReplyKeyboardMarkup(
                    keyboards.STUDENT_INVENTORY, one_time_keyboard=True, resize_keyboard=True
                ),
            )
        else: # if it is a url or a file_id
            await query.message.reply_photo(
                medal.image_url,
                caption=f"{medal.name}\n{medal.description if medal.description else ''}",
                reply_markup=ReplyKeyboardMarkup(
                    keyboards.STUDENT_INVENTORY, one_time_keyboard=True, resize_keyboard=True
                ),
            )
    else:
        await query.message.reply_text(
            f"{medal.name}\n{medal.description if medal.description else ''}",
            reply_markup=ReplyKeyboardMarkup(
                keyboards.STUDENT_INVENTORY, one_time_keyboard=True, resize_keyboard=True
            ),
        )
    return ConversationHandler.END

async def select_medal_back(update: Update, context: ContextTypes):
    """ Returns to student inventory """
    query = update.callback_query
    query.answer()

    # get total credits of the student in this course
    student = student_sql.get_student(user_sql.get_user_by_chatid(update.effective_chat.id).id)
    classroom_id = student.active_classroom_id
    tokens = student_token_sql.get_tokens_by_student_and_classroom(student.id, classroom_id)
    total_credits = sum([token.value for token in tokens])

    await query.message.reply_text(
        f"Tienes {total_credits} créditos",
        reply_markup=ReplyKeyboardMarkup(
            keyboards.STUDENT_INVENTORY, one_time_keyboard=True, resize_keyboard=True
        ),
    )

    return ConversationHandler.END


# Handlers
student_inventory_handler = MessageHandler(filters.Regex("Inventario"), student_inventory)

inv_medal_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Medallas$"), show_medal_list)],
    states={
        states.SI_SELECT_MEDAL: [
            CallbackQueryHandler(select_medal, pattern="^medal#"),
            paginator_handler
            ],
    },
    fallbacks=[
        MessageHandler(filters.Regex("^Atrás$"), back_to_student_menu),
        CallbackQueryHandler(select_medal_back, pattern="^back$"),
    ],
    allow_reentry=True,
)
