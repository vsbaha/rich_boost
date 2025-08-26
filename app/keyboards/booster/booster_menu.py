from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def booster_menu_keyboard():
    """Главное меню для бустеров"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📦 Посмотреть заказы"),
                KeyboardButton(text="💰 Мой баланс")
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="🆘 Поддержка")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )