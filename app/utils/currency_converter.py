import aiohttp
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class CurrencyConverter:
    """Конвертер валют с кэшированием курсов"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(hours=1)  # Обновляем курсы каждый час
        self.last_update = None
        
        # Соответствие валют к их кодам
        self.currency_codes = {
            "сом": "KGS",
            "тенге": "KZT", 
            "руб.": "RUB"
        }
        
        # Базовые курсы (fallback если API не работает)
        self.fallback_rates = {
            "KGS_to_KZT": 5.5,  # 1 сом = 5.5 тенге
            "KGS_to_RUB": 1.1,  # 1 сом = 1.1 рубля
            "KZT_to_RUB": 0.22, # 1 тенге = 0.22 рубля
        }
    
    async def get_exchange_rates(self) -> Dict[str, float]:
        """Получает актуальные курсы валют через API"""
        try:
            # Используем бесплатный API exchangerate-api.com
            async with aiohttp.ClientSession() as session:
                # Получаем курсы относительно USD
                url = "https://api.exchangerate-api.com/v4/latest/USD"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = data.get('rates', {})
                        
                        # Извлекаем нужные курсы
                        usd_to_kgs = rates.get('KGS', 84.0)  # Примерный курс
                        usd_to_kzt = rates.get('KZT', 460.0)  # Примерный курс
                        usd_to_rub = rates.get('RUB', 95.0)   # Примерный курс
                        
                        # Вычисляем кросс-курсы
                        exchange_rates = {
                            "KGS_to_KZT": usd_to_kzt / usd_to_kgs,
                            "KGS_to_RUB": usd_to_rub / usd_to_kgs,
                            "KZT_to_RUB": usd_to_rub / usd_to_kzt,
                            "KZT_to_KGS": usd_to_kgs / usd_to_kzt,
                            "RUB_to_KGS": usd_to_kgs / usd_to_rub,
                            "RUB_to_KZT": usd_to_kzt / usd_to_rub,
                        }
                        
                        logger.info("Курсы валют успешно обновлены через API")
                        self.cache = exchange_rates
                        self.last_update = datetime.now()
                        return exchange_rates
                        
        except Exception as e:
            logger.warning(f"Ошибка получения курсов через API: {e}")
        
        # Если API недоступен, используем fallback курсы
        logger.info("Используются резервные курсы валют")
        return {
            **self.fallback_rates,
            "KZT_to_KGS": 1 / self.fallback_rates["KGS_to_KZT"],
            "RUB_to_KGS": 1 / self.fallback_rates["KGS_to_RUB"],
            "RUB_to_KZT": 1 / self.fallback_rates["KZT_to_RUB"],
        }
    
    async def is_cache_valid(self) -> bool:
        """Проверяет актуальность кэша курсов"""
        if not self.last_update or not self.cache:
            return False
        return datetime.now() - self.last_update < self.cache_duration
    
    async def get_cached_rates(self) -> Dict[str, float]:
        """Получает курсы из кэша или обновляет их"""
        if not await self.is_cache_valid():
            self.cache = await self.get_exchange_rates()
        return self.cache
    
    async def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Конвертирует сумму из одной валюты в другую"""
        if from_currency == to_currency:
            return amount
        
        # Получаем коды валют
        from_code = self.currency_codes.get(from_currency)
        to_code = self.currency_codes.get(to_currency)
        
        if not from_code or not to_code:
            logger.error(f"Неизвестная валюта: {from_currency} -> {to_currency}")
            return amount
        
        # Получаем актуальные курсы
        rates = await self.get_cached_rates()
        
        # Формируем ключ для поиска курса
        rate_key = f"{from_code}_to_{to_code}"
        
        if rate_key in rates:
            converted_amount = amount * rates[rate_key]
            logger.info(f"Конвертация: {amount} {from_currency} = {converted_amount:.2f} {to_currency} (курс: {rates[rate_key]:.4f})")
            return round(converted_amount, 2)
        
        logger.error(f"Курс {rate_key} не найден")
        return amount
    
    def get_currency_symbol(self, currency: str) -> str:
        """Возвращает символ валюты"""
        symbols = {
            "сом": "🇰🇬",
            "тенге": "🇰🇿",
            "руб.": "🇷🇺"
        }
        return symbols.get(currency, "💰")

# Глобальный экземпляр конвертера
converter = CurrencyConverter()

async def convert_booster_balance(amount: float, from_currency: str, to_currency: str) -> float:
    """Удобная функция для конвертации баланса бустера"""
    return await converter.convert_currency(amount, from_currency, to_currency)

async def get_current_rates() -> Dict[str, float]:
    """Получает текущие курсы валют"""
    return await converter.get_cached_rates()
