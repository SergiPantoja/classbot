""" A simple paginator for text messages using inline keyboard buttons as navigation buttons. """
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes


class Paginator():
    def __init__(self, lines: list[str], items_per_page = 10, text_before: str = None, text_after: str = None, page: int = 1, add_back = False, other_buttons: list[InlineKeyboardButton] = None) -> None:
        """ Returns a paginator object. """
        self.lines = lines
        self.items_per_page = items_per_page
        self.text_before = text_before
        self.text_after = text_after
        self.page = page
        self.add_back = add_back
        self.other_buttons = other_buttons

    def text(self) -> str:
        """ Returns the text of the current page. """
        start_index = (self.page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page

        text = ""
        if self.text_before:
            text += self.text_before + "\n\n"
        text += "\n".join(self.lines[start_index:end_index])
        if self.text_after:
            text += "\n\n" + self.text_after

        return text
    
    def keyboard(self) -> InlineKeyboardMarkup:
        """ Returns the keyboard of the current page. """
        keyboard = []
        start_index = (self.page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        
        # add pagination buttons
        if self.page > 1:    # if not in the first page
            if end_index < len(self.lines):  # if not in the first and last page
                keyboard.append([InlineKeyboardButton("<<", callback_data=f"page#{self.page - 1}"), InlineKeyboardButton(">>", callback_data=f"page#{self.page + 1}")])
            else:       # only not in the first page
                keyboard.append([InlineKeyboardButton("<<", callback_data=f"page#{self.page - 1}")])
        elif end_index < len(self.lines):    # if not in the last page
            keyboard.append([InlineKeyboardButton(">>", callback_data=f"page#{self.page + 1}")])
        
        # if other buttons are provided, add them here
        if self.other_buttons:
            keyboard.append(self.other_buttons)
        
        # add back button
        if self.add_back:
            keyboard.append([InlineKeyboardButton("Atrás", callback_data="back")])
        
        return InlineKeyboardMarkup(keyboard)
    
async def update(update: Update, context: ContextTypes) -> None:
    """ Handles pagination. 
    Does not return new state, it will keep a ongoing conversation in the same
    state. This also means it cannot be used as an entry point since it will
    end the conversation."""
    query = update.callback_query
    await query.answer()
    try:
        paginator = context.user_data["paginator"]
    except:
        raise KeyError("No paginator found in user_data. Did you forget to add it?")
    
    paginator.page = int(query.data.split("#")[1])

    keyboard = paginator.keyboard()
    await query.edit_message_text(paginator.text(), reply_markup=keyboard)

text_paginator_handler = CallbackQueryHandler(update, pattern=r"^page#")
