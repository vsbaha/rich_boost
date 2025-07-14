from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def booster_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Заказы")],
            [KeyboardButton(text="💼 Бустерский счёт")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📞 Связь с поддержкой")]
        ],
        resize_keyboard=True
    )