from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_payout_list_keyboard(requests):
    """Клавиатура для списка запросов на выплату"""
    keyboard = []
    
    # Добавляем кнопки для каждого запроса
    for req in requests:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📄 Запрос #{req.id} ({req.amount:.2f})",
                callback_data=f"admin_payout_view_{req.id}"
            )
        ])
    
    # Кнопки управления
    keyboard.extend([
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_payout_requests"),
            InlineKeyboardButton(text="📚 История", callback_data="admin_payout_history")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_payout_detail_keyboard(request_id, status):
    """Клавиатура для детального просмотра запроса"""
    keyboard = []
    
    # Если запрос еще не обработан, показываем кнопки действий
    if status == "pending":
        keyboard.extend([
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve_payout_{request_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_payout_{request_id}")
            ]
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ К списку", callback_data="admin_payout_requests")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_payout_history_keyboard():
    """Клавиатура для истории выплат"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_payout_history"),
            InlineKeyboardButton(text="📋 Текущие", callback_data="admin_payout_requests")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")
        ]
    ])
    return keyboard