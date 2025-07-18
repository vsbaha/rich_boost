import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        f"{log_dir}/bot.log",
        maxBytes=5*1024*1024,  
        backupCount=5,       # Хранить до 5 файлов: bot.log, bot.log.1, ...
        encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )