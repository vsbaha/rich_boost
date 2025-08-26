from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def booster_balance_keyboard():
    """Клавиатура для меню баланса бустера"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить курсы", callback_data="booster_refresh_rates"),
            ],
            [
                InlineKeyboardButton(text="💱 Конвертировать в сомы", callback_data="booster_convert_to:kg"),
                InlineKeyboardButton(text="💱 Конвертировать в тенге", callback_data="booster_convert_to:kz"),
            ],
            [
                InlineKeyboardButton(text="💱 Конвертировать в рубли", callback_data="booster_convert_to:ru"),
            ],
            [
                InlineKeyboardButton(text="📊 Показать курсы", callback_data="booster_show_rates"),
            ]
        ]
    )

def conversion_confirm_keyboard(target_region: str):
    """Клавиатура подтверждения конвертации"""
    region_names = {
        "kg": "сомы 🇰🇬",
        "kz": "тенге 🇰🇿",
        "ru": "рубли 🇷🇺"
    }
    currency_name = region_names.get(target_region, "валюту")
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"✅ Да, конвертировать в {currency_name}", callback_data=f"booster_confirm_convert:{target_region}"),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="booster_cancel_convert"),
            ]
        ]
    )
