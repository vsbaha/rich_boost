from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def booster_balance_keyboard():
    """Клавиатура для меню баланса бустера"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить курсы", callback_data="booster_refresh_rates"),
            ],
            [
                InlineKeyboardButton(text="💱 Конвертировать", callback_data="booster_convert_menu"),
            ],
            [
                InlineKeyboardButton(text="💸 Запросить выплату", callback_data="booster_request_payout"),
                InlineKeyboardButton(text="📋 Мои запросы", callback_data="my_payout_requests"),
            ]
        ]
    )

def booster_convert_menu_keyboard():
    """Клавиатура выбора валюты для конвертации"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇰🇬 В сомы", callback_data="booster_convert_to:kg"),
                InlineKeyboardButton(text="🇰🇿 В тенге", callback_data="booster_convert_to:kz"),
                InlineKeyboardButton(text="🇷🇺 В рубли", callback_data="booster_convert_to:ru"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="booster_cancel_convert_menu"),
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
