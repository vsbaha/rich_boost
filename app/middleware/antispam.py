import time
from aiogram import BaseMiddleware
from aiogram.types import Message

class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0):
        super().__init__()
        self.rate_limit = rate_limit
        self.last_message = {}

    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        now = time.time()
        last = self.last_message.get(user_id, 0)
        if now - last < self.rate_limit:
            await event.answer("⏳ Не спамьте! Подождите немного.")
            return
        self.last_message[user_id] = now
        return await handler(event, data)