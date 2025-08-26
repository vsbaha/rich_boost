import shutil
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler # type: ignore
from aiogram import Bot
from aiogram.types.input_file import FSInputFile
from app.config import DB_PATH, BACKUP_PATH
from app.utils.settings import SettingsManager

async def send_db_backup(bot: Bot):
    # Копируем базу, чтобы не было блокировки
    shutil.copy(DB_PATH, BACKUP_PATH)
    input_file = FSInputFile(BACKUP_PATH)
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    caption = f"Автоматический бэкап базы данных\nДата: {now}"
    
    # Получаем GROUP_ID из настроек
    group_id = await SettingsManager.get_setting("GROUP_ID")
    await bot.send_document(chat_id=group_id, document=input_file, caption=caption)

async def setup_backup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    
    # Получаем час для бэкапа из настроек
    backup_hour = await SettingsManager.get_setting("BACKUP_HOUR")
    scheduler.add_job(send_db_backup, "cron", hour=backup_hour, args=[bot])
    scheduler.start()