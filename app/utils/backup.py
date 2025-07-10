import shutil
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types.input_file import FSInputFile
from app.config import DB_PATH, BACKUP_PATH, GROUP_ID, BACKUP_HOUR

async def send_db_backup(bot: Bot):
    # Копируем базу, чтобы не было блокировки
    shutil.copy(DB_PATH, BACKUP_PATH)
    input_file = FSInputFile(BACKUP_PATH)
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    caption = f"Автоматический бэкап базы данных\nДата: {now}"
    await bot.send_document(chat_id=GROUP_ID, document=input_file, caption=caption)

def setup_backup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_db_backup, "cron", hour=BACKUP_HOUR, args=[bot])
    scheduler.start()