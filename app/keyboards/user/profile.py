from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def user_profile_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Сменить регион", callback_data="user_change_region")],
        ]
    )