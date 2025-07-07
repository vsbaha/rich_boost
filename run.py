import asyncio
import os
from aiogram import Bot, Dispatcher
from app.config import BOT_TOKEN
from app.handlers.common import router as common_router
from app.handlers.admin import router as admin_router
from app.handlers.user import router as user_router
from app.handlers.booster import router as booster_router
from app.database.crud import init_db
from app.middleware.user_update import UserUpdateMiddleware
from app.utils.logger import setup_logging

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

async def main():
    setup_logging()
    clear_console()
    print("=" * 40)
    print("🚀 Boost Bot запущен!")
    print("Для остановки нажмите Ctrl+C")
    print("=" * 40)
    await init_db()  # инициализация БД!
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(booster_router)
    dp.message.middleware(UserUpdateMiddleware())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем (Ctrl+C)")