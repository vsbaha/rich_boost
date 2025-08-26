import json
import logging
from typing import Any, Dict, Optional
from sqlalchemy import select
from app.database.db import AsyncSessionLocal
from app.database.models import BotSettings

logger = logging.getLogger(__name__)

# Настройки по умолчанию
DEFAULT_SETTINGS = {
    # Бэкап
    "GROUP_ID": {
        "value": -1002896042115,
        "description": "ID Tg группы для бэкапа",
        "category": "backup"
    },
    "BACKUP_HOUR": {
        "value": 1,
        "description": "Час отправки бэкапа   (24ч формат)",
        "category": "backup"
    },
    
    # Минимальные суммы пополнения
    "MIN_TOPUP_KGS": {
        "value": 100,
        "description": "🇰🇬 Мин. сумма пополнения в сомах",
        "category": "payments"
    },
    "MIN_TOPUP_KZT": {
        "value": 500,
        "description": "🇰🇿 Мин. сумма пополнения в тенге",
        "category": "payments"
    },
    "MIN_TOPUP_RUB": {
        "value": 200,
        "description": "🇷🇺 Мин. сумма пополнения в рублях",
        "category": "payments"
    },
    
    # Цены за обучение
    "COACHING_PRICES": {
        "value": {
            "🇰🇬 КР": 150,
            "🇰🇿 КЗ": 1500,
            "🇷🇺 РУ": 500
        },
        "description": "Цены за час обучения",
        "category": "prices"
    },
    
    # Множители буста
    "BOOST_MULTIPLIERS": {
        "value": {
            "account": 1.0,
            "shared": 2.5,
            "winrate": 1.5,
            "mmr": 1.0,
            "coaching": 1.0
        },
        "description": "Множители для буста",
        "category": "prices"
    },
    
    # Цены по рангам
    "RANK_PRICES": {
        "value": {
            "🇰🇬 КР": {
                "Воин": 55,
                "Элита": 55,
                "Мастер": 55,
                "Грандмастер": 55,
                "Эпик": 55,
                "Легенда": 55,
                "Мифик": 55,
                "Мифик0-25": 80,
                "Мифик25-50": 90,
                "Мифик50-100": 110,
                "Мифик100+": 130,
            },
            "🇰🇿 КЗ": {
                "Воин": 310,
                "Элита": 310,
                "Мастер": 310,
                "Грандмастер": 310,
                "Эпик": 310,
                "Легенда": 310,
                "Мифик": 310,
                "Мифик0-25": 450,
                "Мифик25-50": 505,
                "Мифик50-100": 620,
                "Мифик100+": 730,
            },
            "🇷🇺 РУ": {
                "Воин": 55,
                "Элита": 55,
                "Мастер": 55,
                "Грандмастер": 55,
                "Эпик": 55,
                "Легенда": 55,
                "Мифик": 55,
                "Мифик0-25": 80,
                "Мифик25-50": 90,
                "Мифик50-100": 110,
                "Мифик100+": 130,
            }
        },
        "description": "Цены по рангам",
        "category": "prices"
    },
    
    # Процент дохода бустеров
    "BOOSTER_INCOME_PERCENT": {
        "value": 70,
        "description": "Процент дохода бустеров от заказа",
        "category": "prices"
    }
}

class SettingsManager:
    """Менеджер настроек бота"""
    
    @staticmethod
    async def get_setting(key: str, default_value: Any = None) -> Any:
        """Получить значение настройки"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(BotSettings).where(BotSettings.key == key)
                )
                setting = result.scalar_one_or_none()
                
                if setting:
                    try:
                        return json.loads(setting.value)
                    except json.JSONDecodeError:
                        # Если не JSON, возвращаем как строку
                        return setting.value
                
                # Если настройка не найдена, возвращаем значение по умолчанию
                if key in DEFAULT_SETTINGS:
                    return DEFAULT_SETTINGS[key]["value"]
                
                return default_value
                
        except Exception as e:
            logger.error(f"Ошибка получения настройки {key}: {e}")
            return default_value
    
    @staticmethod
    async def set_setting(key: str, value: Any, description: str = None, category: str = "general") -> bool:
        """Установить значение настройки"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(BotSettings).where(BotSettings.key == key)
                )
                setting = result.scalar_one_or_none()
                
                # Сериализуем значение в JSON если это не строка
                if isinstance(value, (dict, list, int, float, bool)):
                    value_str = json.dumps(value, ensure_ascii=False)
                else:
                    value_str = str(value)
                
                if setting:
                    # Обновляем существующую настройку
                    setting.value = value_str
                    if description:
                        setting.description = description
                else:
                    # Создаем новую настройку
                    setting = BotSettings(
                        key=key,
                        value=value_str,
                        description=description or DEFAULT_SETTINGS.get(key, {}).get("description", ""),
                        category=category
                    )
                    session.add(setting)
                
                await session.commit()
                logger.info(f"Настройка {key} обновлена: {value}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка установки настройки {key}: {e}")
            return False
    
    @staticmethod
    async def get_all_settings(category: str = None) -> Dict[str, Any]:
        """Получить все настройки или настройки определенной категории"""
        try:
            async with AsyncSessionLocal() as session:
                query = select(BotSettings)
                if category:
                    query = query.where(BotSettings.category == category)
                
                result = await session.execute(query)
                settings = result.scalars().all()
                
                settings_dict = {}
                for setting in settings:
                    try:
                        settings_dict[setting.key] = json.loads(setting.value)
                    except json.JSONDecodeError:
                        settings_dict[setting.key] = setting.value
                
                return settings_dict
                
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {e}")
            return {}
    
    @staticmethod
    async def initialize_default_settings():
        """Инициализировать настройки по умолчанию"""
        try:
            for key, config in DEFAULT_SETTINGS.items():
                # Проверяем, существует ли настройка
                current_value = await SettingsManager.get_setting(key)
                if current_value is None:
                    await SettingsManager.set_setting(
                        key,
                        config["value"],
                        config["description"],
                        config["category"]
                    )
            logger.info("Настройки по умолчанию инициализированы")
        except Exception as e:
            logger.error(f"Ошибка инициализации настроек: {e}")

# Удобные функции для получения конкретных настроек
async def get_group_id() -> int:
    return await SettingsManager.get_setting("GROUP_ID", -1002896042115)

async def get_backup_hour() -> int:
    return await SettingsManager.get_setting("BACKUP_HOUR", 1)

async def get_min_topup_kgs() -> int:
    return await SettingsManager.get_setting("MIN_TOPUP_KGS", 100)

async def get_min_topup_kzt() -> int:
    return await SettingsManager.get_setting("MIN_TOPUP_KZT", 500)

async def get_min_topup_rub() -> int:
    return await SettingsManager.get_setting("MIN_TOPUP_RUB", 200)

async def get_coaching_prices() -> Dict[str, int]:
    return await SettingsManager.get_setting("COACHING_PRICES", {
        "🇰🇬 КР": 150,
        "🇰🇿 КЗ": 1500,
        "🇷🇺 РУ": 500
    })

async def get_boost_multipliers() -> Dict[str, float]:
    return await SettingsManager.get_setting("BOOST_MULTIPLIERS", {
        "account": 1.0,
        "shared": 2.5,
        "winrate": 1.5,
        "mmr": 1.0,
        "coaching": 1.0
    })

async def get_rank_prices() -> Dict[str, Dict[str, int]]:
    return await SettingsManager.get_setting("RANK_PRICES", DEFAULT_SETTINGS["RANK_PRICES"]["value"])

async def get_booster_income_percent() -> int:
    """Получить процент дохода бустеров от заказа"""
    return await SettingsManager.get_setting("BOOSTER_INCOME_PERCENT", DEFAULT_SETTINGS["BOOSTER_INCOME_PERCENT"]["value"])
