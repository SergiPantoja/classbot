""" A paginator for inline keyboard buttons. For selecting among many options. """
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes


ITEMS_PER_PAGE = 5

def paginated_keyboard(buttons: list[InlineKeyboardButton], page: int = 1, context: ContextTypes = None, add_back = False, other_buttons: list[InlineKeyboardButton] = None) -> InlineKeyboardMarkup:
    """ Returns a paginated keyboard. """
    
    # save buttons in user_data
    if context:
        context.user_data["buttons"] = buttons
        context.user_data["add_back"] = add_back
        context.user_data["other_buttons"] = other_buttons

    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE

    # Add buttons of the current page
    keyboard = [[button] for button in buttons[start_index:end_index]]

    # Add pagination buttons
    if page > 1:    # if not in the first page
        if end_index < len(buttons):   # if not in the first and last page
            keyboard.append([InlineKeyboardButton("<<", callback_data=f"page#{page - 1}"), InlineKeyboardButton(">>", callback_data=f"page#{page + 1}")])
        else:       # only not in the first page
            keyboard.append([InlineKeyboardButton("<<", callback_data=f"page#{page - 1}")])
    elif end_index < len(buttons):    # if not in the last page
        keyboard.append([InlineKeyboardButton(">>", callback_data=f"page#{page + 1}")])

    # if other buttons are provided, add them here
    if other_buttons:
        # add them in pairs of two
        for i in range(0, len(other_buttons), 2):
            if i + 1 < len(other_buttons):
                keyboard.append([other_buttons[i], other_buttons[i + 1]])
            else:
                keyboard.append([other_buttons[i]])

    # Add back button
    if add_back:
        keyboard.append([InlineKeyboardButton("🔙", callback_data="back")])

    return InlineKeyboardMarkup(keyboard)

async def paginator(update: Update, context: ContextTypes) -> None:
    """ Handles pagination. 
    Does not return new state, it will keep a ongoing conversation in the same
    state. """
    query = update.callback_query
    await query.answer()

    page = int(query.data.split("#")[1])

    # buttons to pass to paginated_keyboard. Is user_data a good place to store this?
    try:
        buttons = context.user_data["buttons"]
        add_back = context.user_data["add_back"] if "add_back" in context.user_data else False
        other_buttons = context.user_data["other_buttons"] if "other_buttons" in context.user_data else None
    except KeyError:
        raise KeyError("No buttons found in user_data. Did you forget to add them?")
    
    keyboard = paginated_keyboard(buttons, page, add_back=add_back, other_buttons=other_buttons)
    await query.edit_message_reply_markup(keyboard)

paginator_handler = CallbackQueryHandler(paginator, pattern=r"^page#")
