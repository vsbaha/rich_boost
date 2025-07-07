from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def admin_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛠 Админ-панель"), KeyboardButton(text="📦 Все заказы")],
            [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="🎯 Настройки")],
            [KeyboardButton(text="📞 Поддержка")]
        ],
        resize_keyboard=True
    )