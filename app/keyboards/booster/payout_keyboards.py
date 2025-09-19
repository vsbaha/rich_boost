from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.currency import get_currency_info

def get_payout_currency_keyboard():
    """Клавиатура выбора валюты для выплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇰🇬 сом (КР)", callback_data="payout_currency_kg"),
            InlineKeyboardButton(text="🇰🇿 тенге (КЗ)", callback_data="payout_currency_kz")
        ],
        [
            InlineKeyboardButton(text="🇷🇺 руб. (РУ)", callback_data="payout_currency_ru")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_balance")
        ]
    ])
    return keyboard

def get_payout_confirmation_keyboard(amount: float, currency: str):
    """Клавиатура подтверждения запроса выплаты"""
    currency_info = get_currency_info(currency)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_payout_{amount}_{currency}"),
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_payout"),
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_balance")
        ]
    ])
    return keyboard

def get_payout_success_keyboard():
    """Клавиатура после успешного создания запроса выплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Мои запросы", callback_data="my_payout_requests"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="show_balance")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_booster_menu")
        ]
    ])
    return keyboard

def get_my_requests_keyboard():
    """Клавиатура для просмотра своих запросов выплат"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="my_payout_requests"),
            InlineKeyboardButton(text="💸 Новый запрос", callback_data="booster_request_payout")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="show_balance")
        ]
    ])
    return keyboard

def get_back_to_balance_keyboard():
    """Простая клавиатура возврата к балансу"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ К балансу", callback_data="show_balance")
        ]
    ])
    return keyboard

def get_payout_requests_list_keyboard(requests, page=0, per_page=5):
    """Клавиатура со списком запросов выплат с пагинацией"""
    buttons = []
    
    # Вычисляем диапазон для текущей страницы
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_requests = requests[start_idx:end_idx]
    
    # Добавляем кнопки для запросов на текущей странице
    for req in page_requests:
        status_emoji = {
            "pending": "⏳",
            "approved": "✅", 
            "rejected": "❌"
        }.get(req.status, "❓")
        
        currency_info = get_currency_info(req.currency)
        button_text = f"{status_emoji} #{req.id} - {req.amount:.0f} {currency_info['symbol']}"
        
        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"view_payout_request_{req.id}"
            )
        ])
    
    # Пагинация
    pagination_row = []
    total_pages = (len(requests) + per_page - 1) // per_page
    
    if page > 0:
        pagination_row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"payout_requests_page_{page-1}")
        )
    
    pagination_row.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )
    
    if page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"payout_requests_page_{page+1}")
        )
    
    if pagination_row:
        buttons.append(pagination_row)
    
    # Управляющие кнопки
    control_buttons = [
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="my_payout_requests"),
            InlineKeyboardButton(text="💸 Новый запрос", callback_data="booster_request_payout")
        ],
        [
            InlineKeyboardButton(text="◀️ К балансу", callback_data="show_balance")
        ]
    ]
    
    buttons.extend(control_buttons)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def get_payout_request_detail_keyboard(request_id):
    """Клавиатура для детального просмотра запроса"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ К списку запросов", callback_data="return_to_payout_list")
        ],
        [
            InlineKeyboardButton(text="💰 К балансу", callback_data="show_balance")
        ]
    ])
    return keyboard