import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from app.config import BOT_TOKEN
from app.handlers.common import router as common_router
from app.handlers.admin import router as admin_router
from app.handlers.user import router as user_router
from app.handlers.booster import router as booster_router
from app.database.crud import init_db
from app.middleware.user_update import UserUpdateMiddleware
from app.middleware.ban_check import BanCheckMiddleware
from app.middleware.antispam import AntiSpamMiddleware
from app.utils.logger import setup_logging
from app.utils.backup import setup_backup_scheduler 

logging.getLogger("aiogram.event").setLevel(logging.WARNING)

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

async def main():
    setup_logging()
    clear_console()
    print("=" * 40)
    print("🚀 Boost Bot запущен!")
    print("Для остановки нажмите Ctrl+C")
    print("=" * 40)
    await init_db()
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    setup_backup_scheduler(bot)
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(booster_router)
    dp.include_router(common_router)
    dp.message.middleware(UserUpdateMiddleware())
    dp.message.middleware(BanCheckMiddleware())
    dp.message.middleware(AntiSpamMiddleware(rate_limit=1.0))  # 1 сообщение в секунду
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем (Ctrl+C)")