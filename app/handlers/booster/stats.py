from aiogram import Router, F
from aiogram.types import Message
from app.utils.roles import booster_only
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "📊 Статистика")
@booster_only
async def show_booster_stats(message: Message):
    """Показать статистику бустера"""
    from app.database.crud import get_booster_account, get_orders_by_booster, get_user_by_tg_id
    from app.utils.currency_converter import converter
    
    booster_account = await get_booster_account(message.from_user.id)
    if not booster_account:
        await message.answer("❌ Аккаунт бустера не найден!")
        return
    
    orders = await get_orders_by_booster(booster_account.id)
    
    # Получаем пользователя для определения валюты
    user = await get_user_by_tg_id(message.from_user.id)
    region_currencies = {
        "🇰🇬 КР": "сом",
        "🇰🇿 КЗ": "тенге", 
        "🇷🇺 РУ": "руб."
    }
    currency = region_currencies.get(user.region, "руб.") if user else "руб."
    
    # Подсчитываем статистику
    from app.utils.settings import get_booster_income_percent
    booster_percent = await get_booster_income_percent()
    
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o.status == "completed"])
    in_progress_orders = len([o for o in orders if o.status in ["confirmed", "in_progress", "pending_review"]])
    total_earned = sum([o.total_cost * (booster_percent / 100) for o in orders if o.status == "completed"])
    
    # Конвертируем заработанную сумму в доллары
    currency_codes = {"сом": "KGS", "тенге": "KZT", "руб.": "RUB"}
    from_currency = currency_codes.get(currency, "RUB")
    
    try:
        total_earned_usd = await converter.convert_currency(total_earned, from_currency, "USD")
        earned_text = f"💰 <b>Заработано:</b> {total_earned:.0f} {currency} (~${total_earned_usd:.2f})"
    except:
        earned_text = f"💰 <b>Заработано:</b> {total_earned:.0f} {currency}"
    
    await message.answer(
        f"📊 <b>Ваша статистика</b>\n\n"
        f"📦 <b>Всего заказов:</b> {total_orders}\n"
        f"✅ <b>Завершенных:</b> {completed_orders}\n"
        f"🚀 <b>В работе:</b> {in_progress_orders}\n\n"
        f"{earned_text}",
        parse_mode="HTML"
    )
    logger.info(f"Бустер @{message.from_user.username} просмотрел статистику")
