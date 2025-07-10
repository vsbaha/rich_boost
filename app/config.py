import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")

# Пути для бэкапа базы данных
DB_PATH = "rich_boost.db"
BACKUP_PATH = "backup.db"
GROUP_ID = -1002896042115  # ID вашей TG-группы для бэкапа
BACKUP_HOUR = 1  # Время отправки бэкапа (час, 24ч формат)
