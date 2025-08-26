from app.utils.currency import get_active_balance

def format_user_profile(user) -> str:
    balance, bonus, currency = get_active_balance(user)
    date_str = user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else '—'
    
    if user.username:
        username_str = f"@{user.username}"
    else:
        username_str = f'<a href="tg://user?id={user.tg_id}">Связаться</a>'
    
    return (
        f"<b>Профиль пользователя</b>\n"
        f"ID: <code>{user.tg_id}</code>\n"  
        f"Username: {username_str}\n"
        f"Текущий регион: {user.region or '—'}\n"
        f"Роль: {user.role}\n"
        f"Баланс: {balance:.2f} {currency}\n"
        f"Бонусный баланс: {bonus:.2f} {currency}\n"
        f"Дата регистрации: {date_str}"
    )