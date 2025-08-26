from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def my_orders_list_keyboard(orders, show_active_only=True, page=0, per_page=5):
    """Клавиатура со списком заказов бустера с фильтрацией и пагинацией"""
    keyboard = []
    
    # Группируем заказы по статусам
    status_groups = {
        "confirmed": "🔄",
        "in_progress": "🚀", 
        "pending_review": "📋",
        "completed": "✅"
    }
    
    # Фильтруем заказы
    if show_active_only:
        filtered_orders = [o for o in orders if o.status in ["confirmed", "in_progress", "pending_review"]]
    else:
        filtered_orders = orders
    
    # Пагинация
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_orders = filtered_orders[start_idx:end_idx]
    
    # Добавляем заказы
    for order in page_orders:
        status_emoji = status_groups.get(order.status, "❓")
        service_name = {
            "regular_boost": "Обычный буст",
            "hero_boost": "Буст персонажа",
            "coaching": "Гайд/обучение"
        }.get(order.service_type, order.service_type)
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji} Заказ {order.order_id} - {service_name}",
                callback_data=f"booster_order_details:{order.order_id}"
            )
        ])
    
    # Кнопки навигации
    nav_buttons = []
    
    # Кнопки пагинации
    if len(filtered_orders) > per_page:
        pagination_row = []
        
        # Кнопка "назад"
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"booster_orders_page:{show_active_only}:{page-1}")
            )
        
        # Индикатор страницы
        pagination_row.append(
            InlineKeyboardButton(text=f"{page+1}/{(len(filtered_orders)-1)//per_page + 1}", callback_data="noop")
        )
        
        # Кнопка "вперед"
        if end_idx < len(filtered_orders):
            pagination_row.append(
                InlineKeyboardButton(text="➡️", callback_data=f"booster_orders_page:{show_active_only}:{page+1}")
            )
        
        if pagination_row:
            nav_buttons.append(pagination_row)
    
    # Кнопка переключения фильтра
    if show_active_only:
        nav_buttons.append([
            InlineKeyboardButton(text="📋 Показать все заказы", callback_data="booster_orders_filter:all:0")
        ])
    else:
        nav_buttons.append([
            InlineKeyboardButton(text="🔄 Показать только активные", callback_data="booster_orders_filter:active:0")
        ])
    
    # Кнопка обновления
    nav_buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="booster_refresh_orders")
    ])
    
    keyboard.extend(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def order_management_keyboard(order_id, status):
    """Клавиатура управления заказом"""
    keyboard = []
    
    if status == "confirmed":
        keyboard.append([
            InlineKeyboardButton(text="🚀 Начать работу", callback_data=f"booster_start_work:{order_id}")
        ])
    elif status == "in_progress":
        keyboard.extend([
            [InlineKeyboardButton(text="🔒 Управление аккаунтом", callback_data=f"booster_take_account:{order_id}"),
             InlineKeyboardButton(text="✅ Завершить заказ", callback_data=f"booster_complete_order:{order_id}")]
        ])
    elif status == "pending_review":
        keyboard.append([
            InlineKeyboardButton(text="⏳ Ожидает проверки", callback_data="noop")
        ])
    elif status == "completed":
        keyboard.append([
            InlineKeyboardButton(text="✅ Заказ завершен", callback_data="noop")
        ])
    elif status == "paused":
        keyboard.append([
            InlineKeyboardButton(text="⏸️ Заказ приостановлен", callback_data="noop")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="📦 Мои заказы", callback_data="booster_refresh_orders")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def booster_order_details_keyboard(order_id, status):
    """Клавиатура с деталями заказа для бустера"""
    keyboard = []
    
    if status == "confirmed":
        keyboard.append([
            InlineKeyboardButton(text="🚀 Начать работу", callback_data=f"booster_start_work:{order_id}")
        ])
    elif status == "in_progress":
        keyboard.extend([
            [InlineKeyboardButton(text="🔒 Управление аккаунтом", callback_data=f"booster_take_account:{order_id}"),
             InlineKeyboardButton(text="✅ Завершить заказ", callback_data=f"booster_complete_order:{order_id}")]
        ])
    elif status == "pending_review":
        keyboard.append([
            InlineKeyboardButton(text="⏳ Ожидает проверки", callback_data="noop")
        ])
    elif status == "completed":
        keyboard.append([
            InlineKeyboardButton(text="✅ Заказ завершен", callback_data="noop")
        ])
    elif status == "paused":
        keyboard.append([
            InlineKeyboardButton(text="⏸️ Заказ приостановлен", callback_data="noop")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🔙 К списку заказов", callback_data="booster_refresh_orders")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def account_management_keyboard(order_id, is_account_taken=False):
    """Клавиатура управления аккаунтом"""
    keyboard = []
    
    if is_account_taken:
        keyboard.append([
            InlineKeyboardButton(text="🔓 Покинуть аккаунт", callback_data=f"booster_leave_account:{order_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="🔒 Занять аккаунт", callback_data=f"booster_take_account:{order_id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад к заказу", callback_data=f"booster_order_details:{order_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def booster_work_progress_keyboard(order_id, account_taken=False, status="in_progress"):
    """Клавиатура прогресса работы бустера"""
    keyboard = []
    
    # Кнопки управления аккаунтом
    if account_taken:
        keyboard.append([
            InlineKeyboardButton(text="🔓 Покинуть аккаунт", callback_data=f"booster_leave_account:{order_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="🔒 Занять аккаунт", callback_data=f"booster_take_account:{order_id}")
        ])
    
    # Основные кнопки - показываем "Завершить заказ" только если заказ не завершен
    if status == "in_progress":
        keyboard.append([InlineKeyboardButton(text="✅ Завершить заказ", callback_data=f"booster_complete_order:{order_id}")])
    elif status == "pending_review":
        keyboard.append([InlineKeyboardButton(text="⏳ Ожидает проверки", callback_data="noop")])
    elif status == "completed":
        keyboard.append([InlineKeyboardButton(text="✅ Заказ завершен", callback_data="noop")])
    elif status == "paused":
        keyboard.append([InlineKeyboardButton(text="⏸️ Заказ приостановлен", callback_data="noop")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 К списку заказов", callback_data="booster_refresh_orders")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def booster_complete_order_keyboard(order_id):
    """Клавиатура завершения заказа"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад к заказу", callback_data=f"booster_order_details:{order_id}")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
