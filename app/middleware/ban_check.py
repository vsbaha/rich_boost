from aiogram.dispatcher.middlewares.base import BaseMiddleware
from app.database.crud import get_user_by_tg_id
from aiogram.types import Message

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            user = await get_user_by_tg_id(event.from_user.id)
            if user and user.role == "banned":
                await event.answer("⛔️ Ваш аккаунт заблокирован. Обратитесь в поддержку. @kkm1s")
                return  # Не передаём управление дальше
        return await handler(event, data)