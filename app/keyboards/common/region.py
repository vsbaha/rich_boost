from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def region_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇰🇬 КР"), KeyboardButton(text="🇰🇿 КЗ")],
            [KeyboardButton(text="🇷🇺 РУ")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    