from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_payment_keyboard(request_id, user_tg_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_payment:{request_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment:{request_id}")
            ],
            [
                InlineKeyboardButton(
                    text="👤 Посмотреть профиль",
                    callback_data=f"payment_user_info:{user_tg_id}:{request_id}"
                )
            ]
        ]
    )

def back_to_payment_keyboard(request_id, user):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Вернуться к заявке",
                    callback_data=f"back_to_payment:{request_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Забанить" if user.role != "banned" else "✅ Разбанить",
                    callback_data=f"user_ban:{user.tg_id}:{request_id}" if user.role != "banned" else f"user_unban:{user.tg_id}:{request_id}"
                ),
                InlineKeyboardButton(
                    text="💸 Изменить баланс",
                    callback_data=f"user_balance:{user.tg_id}:{request_id}"
                ),
                InlineKeyboardButton(
                    text="🎁 Изменить бонус",
                    callback_data=f"user_bonus:{user.tg_id}:{request_id}"
                )
            ]
        ]
    )

def admin_topup_action_keyboard(request_id, status, filter_status, user_tg_id=None):
    buttons = []
    if status == "pending":
        buttons.append([
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"accept_payment:{request_id}:filter:{filter_status}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment:{request_id}:filter:{filter_status}")
        ])
        # Кнопка "Посмотреть профиль"
        if user_tg_id:
            buttons.append([
                InlineKeyboardButton(
                    text="👤 Посмотреть профиль",
                    callback_data=f"payment_user_info:{user_tg_id}:{request_id}"
                )
            ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_filtered:{filter_status}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)