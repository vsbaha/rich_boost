import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import BOT_TOKEN
from app.handlers.common import router as common_router
from app.database.crud import init_db
import os

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(f"{log_dir}/bot.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

async def main():
    clear_console()
    setup_logging()
    await init_db()  # ← добавь эту строку!
    print("=" * 40)
    print("🚀 Boost Bot запущен!")
    print("Для остановки нажмите Ctrl+C")
    print("=" * 40)
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    # Импорт и регистрация роутеров
    dp.include_router(common_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем (Ctrl+C)")