import logging
from aiogram import BaseMiddleware
from app.database.crud import update_user_username

logger = logging.getLogger(__name__)

class UserUpdateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if user:
            await update_user_username(user.id, user.username or "")
        return await handler(event, data)