from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_order_notification_keyboard(order_id: str):
    """Клавиатура для уведомления админа о новом заказе"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Назначить бустера", callback_data=f"admin_assign_booster:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_order:{order_id}")
        ],
        [
            InlineKeyboardButton(text="📋 Подробнее", callback_data=f"admin_order_details:{order_id}")
        ]
    ])

def admin_order_details_keyboard(order_id: str, status: str = "pending"):
    """Клавиатура для детального управления заказом"""
    keyboard = []
    
    if status == "pending":
        keyboard.append([
            InlineKeyboardButton(text="👥 Назначить бустера", callback_data=f"admin_assign_booster:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить заказ", callback_data=f"admin_reject_order:{order_id}")
        ])
    
    if status == "confirmed":
        keyboard.append([
            InlineKeyboardButton(text="🚀 Взять в работу", callback_data=f"admin_start_order:{order_id}"),
            InlineKeyboardButton(text="⏸️ Приостановить", callback_data=f"admin_pause_order:{order_id}")
        ])
        # Позволяем переназначить бустера если нужно
        keyboard.append([
            InlineKeyboardButton(text="👥 Переназначить бустера", callback_data=f"admin_assign_booster:{order_id}")
        ])
    
    if status == "in_progress":
        keyboard.append([
            InlineKeyboardButton(text="✅ Завершить", callback_data=f"admin_complete_order:{order_id}"),
            InlineKeyboardButton(text="⏸️ Приостановить", callback_data=f"admin_pause_order:{order_id}")
        ])
    
    if status == "paused":
        keyboard.append([
            InlineKeyboardButton(text="▶️ Возобновить", callback_data=f"admin_resume_order:{order_id}"),
            InlineKeyboardButton(text="✅ Завершить", callback_data=f"admin_complete_order:{order_id}")
        ])
    
    if status == "pending_review":
        keyboard.append([
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve_completion:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_completion:{order_id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="👤 Профиль клиента", callback_data=f"admin_client_profile:{order_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton(text="🗂️ Все заказы", callback_data="admin_orders_list"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_boosters_list_keyboard(order_id: str, boosters: list, page: int = 0):
    """Клавиатура для выбора бустера"""
    keyboard = []
    per_page = 5
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    # Бустеры на текущей странице
    for booster in boosters[start_idx:end_idx]:
        status_emoji = "🟢" if booster.status == "active" else "🔴"
        button_text = f"{status_emoji} {booster.username or f'ID:{booster.user_id}'}"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text, 
                callback_data=f"admin_select_booster:{order_id}:{booster.user_id}"
            )
        ])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_boosters_page:{order_id}:{page-1}"))
    if end_idx < len(boosters):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_boosters_page:{order_id}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton(text="🔙 К заказу", callback_data=f"admin_order_details:{order_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_orders_list_keyboard(page: int = 0, status_filter: str = "all"):
    """Клавиатура для списка заказов с фильтрами"""
    keyboard = []
    
    # Фильтры по статусу
    status_filters = [
        ("📋 Все", "all"),
        ("⏳ Ожидающие", "pending"),
        ("✅ Подтвержденные", "confirmed"),
        ("🚀 В работе", "in_progress"),
        ("⏸️ Приостановленные", "paused"),
        ("✅ Завершенные", "completed"),
        ("❌ Отмененные", "cancelled")
    ]
    
    filter_row = []
    for text, status in status_filters:
        emoji = "🔹" if status == status_filter else ""
        button_text = f"{emoji}{text}"
        filter_row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"admin_orders_filter:{status}:0"
            )
        )
        
        if len(filter_row) == 3:
            keyboard.append(filter_row)
            filter_row = []
    
    if filter_row:
        keyboard.append(filter_row)
    
    # Навигация по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_orders_page:{status_filter}:{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_search_order"))
    nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_orders_page:{status_filter}:{page+1}"))
    
    keyboard.append(nav_buttons)
    
    # Возврат в главное меню
    keyboard.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def confirm_action_keyboard(action: str, order_id: str):
    """Клавиатура подтверждения действия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{action}:{order_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_order_details:{order_id}")
        ]
    ])
