from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.utils.roles import admin_only
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("rates"))
@admin_only
async def show_currency_rates(message: Message):
    """Показать текущие курсы валют (админ команда)"""
    from app.utils.currency_converter import get_current_rates
    
    try:
        rates = await get_current_rates()
        
        text = "📊 <b>Текущие курсы валют</b>\n\n"
        text += "<b>Основные курсы:</b>\n"
        text += f"🇰🇬→🇰🇿 1 сом = <b>{rates.get('KGS_to_KZT', 0):.3f}</b> тенге\n"
        text += f"🇰🇬→🇷🇺 1 сом = <b>{rates.get('KGS_to_RUB', 0):.3f}</b> руб.\n"
        text += f"🇰🇿→🇷🇺 1 тенге = <b>{rates.get('KZT_to_RUB', 0):.3f}</b> руб.\n\n"
        
        text += "<b>Обратные курсы:</b>\n"
        text += f"🇰🇿→🇰🇬 1 тенге = <b>{rates.get('KZT_to_KGS', 0):.3f}</b> сом\n"
        text += f"🇷🇺→🇰🇬 1 руб. = <b>{rates.get('RUB_to_KGS', 0):.3f}</b> сом\n"
        text += f"🇷🇺→🇰🇿 1 руб. = <b>{rates.get('RUB_to_KZT', 0):.3f}</b> тенге\n\n"
        
        text += "💡 <i>Курсы обновляются автоматически каждый час через API</i>"
        
        await message.answer(text, parse_mode="HTML")
        logger.info(f"Админ @{message.from_user.username} проверил курсы валют")
        
    except Exception as e:
        logger.error(f"Ошибка получения курсов: {e}")
        await message.answer(
            "❌ <b>Ошибка получения курсов</b>\n\n"
            "Не удалось получить актуальные курсы валют.\n"
            "Проверьте подключение к интернету.",
            parse_mode="HTML"
        )
