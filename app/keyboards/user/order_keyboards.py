from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import RANKS, LANES, MAIN_RANKS, RANK_GRADATIONS

def service_catalog_keyboard():
    """Клавиатура каталога услуг"""
    buttons = [
        [InlineKeyboardButton(text="🎮 Обычный буст", callback_data="service:regular_boost")],
        [InlineKeyboardButton(text="🎯 Буст персонажа", callback_data="service:hero_boost")],
        [InlineKeyboardButton(text="📚 Гайд / обучение", callback_data="service:coaching")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]  # Оставляем тут
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def regular_boost_type_keyboard():
    """Клавиатура типов обычного буста"""
    buttons = [
        [InlineKeyboardButton(text="🔐 Через вход на аккаунт", callback_data="boost_type:account")],
        [InlineKeyboardButton(text="🤝 Совместный буст", callback_data="boost_type:shared")],
        [InlineKeyboardButton(text="📊 Буст ММР", callback_data="boost_type:mmr")],
        [InlineKeyboardButton(text="📈 Буст винрейта", callback_data="boost_type:winrate")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_catalog")]
        # Убираем кнопку "Отмена"
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def hero_boost_type_keyboard():
    """Клавиатура типов буста персонажа"""
    buttons = [
        [InlineKeyboardButton(text="🔐 Через вход на аккаунт", callback_data="boost_type:account")],
        [InlineKeyboardButton(text="🤝 Совместный буст", callback_data="boost_type:shared")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_catalog")]
        # Убираем кнопку "Отмена"
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def main_ranks_keyboard():
    """Клавиатура основных рангов"""
    buttons = []
    for rank in MAIN_RANKS:
        buttons.append([InlineKeyboardButton(text=rank, callback_data=f"main_rank:{rank}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_boost_type")])
    # Убираем кнопку "Отмена"
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def rank_gradations_keyboard(main_rank):
    """Клавиатура градаций ранга"""
    gradations = RANK_GRADATIONS.get(main_rank, [])
    
    buttons = []
    for gradation in gradations:
        buttons.append([InlineKeyboardButton(text=gradation, callback_data=f"rank:{gradation}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_ranks")])
    # Убираем кнопку "Отмена"
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def target_main_ranks_keyboard(current_rank):
    """Клавиатура основных целевых рангов"""
    valid_main_ranks = get_valid_main_ranks(current_rank)
    
    buttons = []
    for rank in valid_main_ranks:
        buttons.append([InlineKeyboardButton(text=rank, callback_data=f"target_main_rank:{rank}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_current_rank")])
    # Убираем кнопку "Отмена"
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def target_rank_gradations_keyboard(main_rank, current_rank):
    """Клавиатура градаций целевого ранга"""
    gradations = RANK_GRADATIONS.get(main_rank, [])
    
    # Если это тот же основной ранг, фильтруем градации
    if get_main_rank_from_full(current_rank) == main_rank:
        gradations = get_valid_gradations(current_rank, gradations)
    
    if not gradations:
        buttons = [
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_target_main_ranks")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    buttons = []
    for gradation in gradations:
        buttons.append([InlineKeyboardButton(text=gradation, callback_data=f"rank:{gradation}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_target_main_ranks")])
    # Убираем кнопку "Отмена"
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def lanes_keyboard():
    """Клавиатура выбора лайнов"""
    buttons = []
    for lane in LANES:
        buttons.append([InlineKeyboardButton(text=lane, callback_data=f"lane:{lane}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_game_id")])
    # Убираем кнопку "Отмена"
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_order_keyboard():
    """Клавиатура подтверждения заказа"""
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_order")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]  # Оставляем тут
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_keyboard():
    """Клавиатура только с отменой - для ввода текста"""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_keyboard(callback_data):
    """Универсальная клавиатура с кнопкой "Назад" """
    buttons = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_valid_target_ranks(current_rank):
    """Возвращает список допустимых целевых рангов"""
    if current_rank == "Mythic":
        return ["Mythic"]  # Только Mythic с большим количеством звезд
    
    try:
        current_index = RANKS.index(current_rank)
        return RANKS[current_index + 1:]  # Все ранги выше текущего
    except ValueError:
        return RANKS  # Если что-то пошло не так, возвращаем все ранги

def target_ranks_keyboard(current_rank, page=0, per_page=10):
    """Клавиатура для выбора целевых рангов с валидацией"""
    valid_ranks = get_valid_target_ranks(current_rank)
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    ranks_slice = valid_ranks[start_idx:end_idx]
    
    buttons = []
    for rank in ranks_slice:
        buttons.append([InlineKeyboardButton(text=rank, callback_data=f"rank:{rank}")])
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"target_ranks_page:{page-1}"))
    if end_idx < len(valid_ranks):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"target_ranks_page:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_rank_from_full(full_rank):
    """Извлекает основной ранг из полного названия"""
    for main_rank in MAIN_RANKS:
        if main_rank in full_rank:
            return main_rank
    return "Воин"  # По умолчанию

def get_valid_main_ranks(current_rank):
    """Возвращает список допустимых основных рангов"""
    if current_rank == "Мифик":
        return ["Мифик"]
    
    current_main_rank = get_main_rank_from_full(current_rank)
    try:
        current_index = MAIN_RANKS.index(current_main_rank)
        # Если у нас текущий ранг не максимальный в своей категории, показываем тот же ранг
        # Если максимальный - показываем следующие ранги
        
        # Проверяем, максимальный ли это ранг в категории
        gradations = RANK_GRADATIONS.get(current_main_rank, [])
        is_max_in_category = current_rank == gradations[-1] if gradations else True
        
        if is_max_in_category:
            # Если максимальный ранг в категории - показываем следующие категории
            return MAIN_RANKS[current_index + 1:]
        else:
            # Если не максимальный - показываем ту же категорию и следующие
            return MAIN_RANKS[current_index:]
            
    except ValueError:
        return MAIN_RANKS

def get_valid_gradations(current_rank, gradations):
    """Возвращает допустимые градации для того же основного ранга"""
    try:
        current_index = gradations.index(current_rank)
        return gradations[current_index + 1:]  # Только выше текущего
    except ValueError:
        return gradations