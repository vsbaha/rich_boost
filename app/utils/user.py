from app.utils.currency import get_active_balance

def format_user_profile(user) -> str:
    balance, bonus, currency = get_active_balance(user)
    return (
        f"<b>Профиль пользователя</b>\n"
        f"ID: <code>{user.tg_id}</code>\n"
        f"Username: @{user.username or '—'}\n"
        f"Текущий регион: {user.region or '—'}\n"
        f"Роль: {user.role}\n"
        f"Баланс: {balance:.2f} {currency}\n"
        f"Бонусный баланс: {bonus:.2f} {currency}\n"
        f"Дата регистрации: {user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else '—'}"
    )