from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def user_balance_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Пополнить баланс", callback_data="user_topup")],
            [InlineKeyboardButton(text="📜 История операций", callback_data="user_history")]
        ]
    )