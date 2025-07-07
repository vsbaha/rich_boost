from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Создать заказ"), KeyboardButton(text="📦 Мои заказы")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🎟 Бонусы и рефералы"), KeyboardButton(text="📞 Связь с поддержкой")]
        ],
        resize_keyboard=True
    )