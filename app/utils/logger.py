import logging
import os

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