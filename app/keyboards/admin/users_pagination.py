from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def users_pagination_keyboard(users, page: int, total_pages: int):
    keyboard = []
    for user in users:
        btn_text = f"@{user.username or '—'} | {user.region or '—'} | {user.role}"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"user_info:{user.tg_id}")])
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"users_page:{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text="🔍 Поиск", callback_data="users_search"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"users_page:{page+1}"))
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(text="📢 Рассылка всем", callback_data="users_broadcast")])
    keyboard.append([InlineKeyboardButton(text="📢 Рассылка бустерам", callback_data="boosters_broadcast")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def users_search_keyboard(users):
    keyboard = []
    for user in users:
        btn_text = f"ID: {user.tg_id} | @{user.username or '—'} | {user.region or '—'} | {user.role}"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"user_info:{user.tg_id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="users_page:1")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def user_profile_keyboard(user):
    buttons = [
        [
            InlineKeyboardButton(
                text="🚫 Забанить" if user.role != "banned" else "✅ Разбанить",
                callback_data=f"user_ban:{user.tg_id}" if user.role != "banned" else f"user_unban:{user.tg_id}"
            ),
            InlineKeyboardButton(text="💸 Изменить баланс", callback_data=f"user_balance:{user.tg_id}"),
            InlineKeyboardButton(text="🎁 Изменить бонус", callback_data=f"user_bonus:{user.tg_id}")
        ],
        [
            InlineKeyboardButton(
                text="⭐ Назначить бустером" if user.role != "booster" else "❌ Снять бустера",
                callback_data=f"user_set_booster:{user.tg_id}" if user.role != "booster" else f"user_unset_booster:{user.tg_id}"
            )
        ],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="users_page:1")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)