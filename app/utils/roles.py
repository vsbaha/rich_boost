from functools import wraps
from app.database.crud import get_user_by_tg_id

def role_required(role: str):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message, *args, **kwargs):
            user = await get_user_by_tg_id(message.from_user.id)
            if not user or user.role != role:
                await message.answer(
                    f"⛔️ У вас нет доступа к этой функции.\n"
                    f"Требуется роль: <b>{role.capitalize()}</b>.",
                    parse_mode="HTML"
                )
                return
            return await handler(message, *args, **kwargs)
        return wrapper
    return decorator

admin_only = role_required("admin")
booster_only = role_required("booster")