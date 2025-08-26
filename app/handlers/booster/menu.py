from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.utils.roles import booster_only
from app.keyboards.booster.booster_menu import booster_menu_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("menu"))
@booster_only
async def booster_menu_command(message: Message):
    """Отображение главного меню бустера"""
    await message.answer(
        "🎮 <b>Меню бустера</b>\n\n"
        "Добро пожаловать в панель бустера!\n"
        "Выберите нужный раздел:",
        parse_mode="HTML",
        reply_markup=booster_menu_keyboard()
    )
    logger.info(f"Бустер @{message.from_user.username} открыл главное меню")

@router.message(F.text == "💰 Мой баланс")
@booster_only
async def show_booster_balance(message: Message):
    """Показать баланс бустера с возможностью конвертации"""
    from app.database.crud import get_booster_account, get_user_by_tg_id, get_booster_total_balance_in_currency
    from app.keyboards.booster.balance_menu import booster_balance_keyboard
    
    booster_account = await get_booster_account(message.from_user.id)
    if not booster_account:
        await message.answer("❌ Аккаунт бустера не найден!")
        return
    
    # Получаем пользователя для определения региона
    user = await get_user_by_tg_id(message.from_user.id)
    region_currencies = {
        "🇰🇬 КР": "сом",
        "🇰🇿 КЗ": "тенге", 
        "🇷🇺 РУ": "руб."
    }
    user_currency = region_currencies.get(user.region, "руб.") if user else "руб."
    
    # Показываем детальную информацию по всем валютам
    text = "💰 <b>Ваш бустерский баланс</b>\n\n"
    
    # Балансы по валютам
    if booster_account.balance_kg > 0:
        text += f"🇰🇬 <b>{booster_account.balance_kg:.2f} сом</b>\n"
    if booster_account.balance_kz > 0:
        text += f"🇰🇿 <b>{booster_account.balance_kz:.2f} тенге</b>\n"  
    if booster_account.balance_ru > 0:
        text += f"🇷🇺 <b>{booster_account.balance_ru:.2f} руб.</b>\n"
    
    # Общий баланс в валюте пользователя
    total_balance = await get_booster_total_balance_in_currency(user.id, user_currency)
    text += f"\n� <b>Общий баланс:</b> {total_balance:.2f} {user_currency}\n\n"
    text += "💡 <i>Средства начисляются по курсу валюты заказа</i>"
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=booster_balance_keyboard()
    )
    logger.info(f"Бустер @{message.from_user.username} проверил баланс: общий {total_balance} {user_currency}")

@router.message(F.text == "📊 Статистика")
@booster_only
async def show_booster_stats(message: Message):
    """Показать статистику бустера"""
    from app.database.crud import get_booster_account, get_orders_by_booster, get_user_by_tg_id
    
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
    
    # Получаем баланс в валюте региона бустера
    currency_balances = {
        "сом": booster_account.balance_kg,
        "тенге": booster_account.balance_kz,
        "руб.": booster_account.balance_ru
    }
    balance = currency_balances.get(currency, booster_account.balance_ru)
    
    # Подсчитываем статистику
    from app.utils.settings import get_booster_income_percent
    booster_percent = await get_booster_income_percent()
    
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o.status == "completed"])
    in_progress_orders = len([o for o in orders if o.status in ["confirmed", "in_progress", "pending_review"]])
    total_earned = sum([o.total_cost * (booster_percent / 100) for o in orders if o.status == "completed"])
    
    await message.answer(
        f"📊 <b>Ваша статистика</b>\n\n"
        f"📦 <b>Всего заказов:</b> {total_orders}\n"
        f"✅ <b>Завершенных:</b> {completed_orders}\n"
        f"🚀 <b>В работе:</b> {in_progress_orders}\n\n"
        f"💰 <b>Заработано:</b> {total_earned:.0f} {currency}\n"
        f"💳 <b>На балансе:</b> {balance:.2f} {currency}\n\n"
        f"📈 <b>Рейтинг качества:</b> ⭐⭐⭐⭐⭐",
        parse_mode="HTML"
    )
    logger.info(f"Бустер @{message.from_user.username} просмотрел статистику")

# === ОБРАБОТЧИКИ КОНВЕРТАЦИИ БАЛАНСА ===

@router.callback_query(F.data == "booster_refresh_rates")
@booster_only
async def refresh_exchange_rates(call: CallbackQuery):
    """Обновление курсов валют"""
    from app.utils.currency_converter import get_current_rates
    
    await call.answer("🔄 Обновляем курсы валют...")
    
    try:
        rates = await get_current_rates()
        
        text = "📊 <b>Актуальные курсы валют</b>\n\n"
        text += f"🇰🇬→🇰🇿 1 сом = {rates.get('KGS_to_KZT', 0):.3f} тенге\n"
        text += f"🇰🇬→🇷🇺 1 сом = {rates.get('KGS_to_RUB', 0):.3f} руб.\n"
        text += f"🇰🇿→🇷🇺 1 тенге = {rates.get('KZT_to_RUB', 0):.3f} руб.\n\n"
        text += "💡 <i>Курсы обновляются автоматически каждый час</i>"
        
        await call.message.edit_text(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка обновления курсов: {e}")
        await call.message.edit_text(
            "❌ <b>Ошибка обновления курсов</b>\n\n"
            "Не удалось получить актуальные курсы валют.\n"
            "Попробуйте позже.",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "booster_show_rates")
@booster_only
async def show_exchange_rates(call: CallbackQuery):
    """Показать текущие курсы валют"""
    from app.utils.currency_converter import get_current_rates
    
    try:
        rates = await get_current_rates()
        
        text = "📊 <b>Текущие курсы валют</b>\n\n"
        text += f"🇰🇬→🇰🇿 1 сом = {rates.get('KGS_to_KZT', 0):.3f} тенге\n"
        text += f"🇰🇬→🇷🇺 1 сом = {rates.get('KGS_to_RUB', 0):.3f} руб.\n"
        text += f"🇰🇿→🇰🇬 1 тенге = {rates.get('KZT_to_KGS', 0):.3f} сом\n"
        text += f"🇰🇿→🇷🇺 1 тенге = {rates.get('KZT_to_RUB', 0):.3f} руб.\n"
        text += f"🇷🇺→🇰🇬 1 руб. = {rates.get('RUB_to_KGS', 0):.3f} сом\n"
        text += f"🇷🇺→🇰🇿 1 руб. = {rates.get('RUB_to_KZT', 0):.3f} тенге\n\n"
        text += "💡 <i>Данные обновляются каждый час</i>"
        
        await call.answer()
        await call.message.edit_text(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка получения курсов: {e}")
        await call.answer("❌ Ошибка получения курсов", show_alert=True)

@router.callback_query(F.data.startswith("booster_convert_to:"))
@booster_only
async def start_balance_conversion(call: CallbackQuery):
    """Начать конвертацию баланса в выбранную валюту"""
    from app.database.crud import get_booster_account, get_user_by_tg_id, get_booster_total_balance_in_currency
    from app.keyboards.booster.balance_menu import conversion_confirm_keyboard
    
    target_region_code = call.data.split(":")[1]
    
    # Получаем информацию о бустере
    booster_account = await get_booster_account(call.from_user.id)
    user = await get_user_by_tg_id(call.from_user.id)
    
    if not booster_account or not user:
        await call.answer("❌ Ошибка получения данных", show_alert=True)
        return
    
    # Определяем целевую валюту
    region_map = {
        "kg": ("🇰🇬 КР", "сом"),
        "kz": ("🇰🇿 КЗ", "тенге"), 
        "ru": ("🇷🇺 РУ", "руб.")
    }
    target_region, target_currency = region_map.get(target_region_code, ("🇷🇺 РУ", "руб."))
    
    # Подсчитываем общий баланс в целевой валюте
    try:
        total_balance = await get_booster_total_balance_in_currency(user.id, target_currency)
        
        # Проверяем, есть ли что конвертировать
        if total_balance <= 0:
            await call.answer("❌ Нет средств для конвертации", show_alert=True)
            return
        
        # Показываем детали конвертации
        text = f"💱 <b>Конвертация баланса</b>\n\n"
        text += f"Текущие балансы:\n"
        if booster_account.balance_kg > 0:
            text += f"🇰🇬 {booster_account.balance_kg:.2f} сом\n"
        if booster_account.balance_kz > 0:
            text += f"🇰🇿 {booster_account.balance_kz:.2f} тенге\n"
        if booster_account.balance_ru > 0:
            text += f"🇷🇺 {booster_account.balance_ru:.2f} руб.\n"
        
        text += f"\n➡️ <b>После конвертации:</b>\n"
        text += f"{region_map[target_region_code][0]} {total_balance:.2f} {target_currency}\n\n"
        text += "⚠️ <i>Конвертация необратима!</i>"
        
        await call.message.edit_text(
            text, 
            parse_mode="HTML",
            reply_markup=conversion_confirm_keyboard(target_region_code)
        )
        
    except Exception as e:
        logger.error(f"Ошибка расчета конвертации: {e}")
        await call.answer("❌ Ошибка расчета конвертации", show_alert=True)

@router.callback_query(F.data.startswith("booster_confirm_convert:"))
@booster_only  
async def confirm_balance_conversion(call: CallbackQuery):
    """Подтвердить конвертацию баланса"""
    from app.database.crud import convert_booster_balance_to_region, get_user_by_tg_id
    
    target_region_code = call.data.split(":")[1]
    user = await get_user_by_tg_id(call.from_user.id)
    
    if not user:
        await call.answer("❌ Ошибка получения данных", show_alert=True)
        return
    
    # Определяем целевой регион
    region_map = {
        "kg": "🇰🇬 КР",
        "kz": "🇰🇿 КЗ", 
        "ru": "🇷🇺 РУ"
    }
    target_region = region_map.get(target_region_code, "🇷🇺 РУ")
    
    try:
        success, message = await convert_booster_balance_to_region(user.id, target_region)
        
        if success:
            await call.message.edit_text(
                f"✅ <b>Конвертация завершена!</b>\n\n{message}",
                parse_mode="HTML"
            )
            logger.info(f"Бустер @{call.from_user.username} сконвертировал баланс в {target_region}")
        else:
            await call.message.edit_text(
                f"❌ <b>Ошибка конвертации</b>\n\n{message}",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Ошибка конвертации баланса: {e}")
        await call.message.edit_text(
            "❌ <b>Ошибка конвертации</b>\n\nПроизошла техническая ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "booster_cancel_convert")
@booster_only
async def cancel_balance_conversion(call: CallbackQuery):
    """Отменить конвертацию баланса"""
    await call.answer("Конвертация отменена")
    
    # Возвращаемся к меню баланса
    from app.database.crud import get_booster_account, get_user_by_tg_id, get_booster_total_balance_in_currency
    from app.keyboards.booster.balance_menu import booster_balance_keyboard
    
    booster_account = await get_booster_account(call.from_user.id)
    user = await get_user_by_tg_id(call.from_user.id)
    
    if booster_account and user:
        region_currencies = {
            "🇰🇬 КР": "сом",
            "🇰🇿 КЗ": "тенге", 
            "🇷🇺 РУ": "руб."
        }
        user_currency = region_currencies.get(user.region, "руб.")
        
        text = "💰 <b>Ваш бустерский баланс</b>\n\n"
        
        if booster_account.balance_kg > 0:
            text += f"🇰🇬 <b>{booster_account.balance_kg:.2f} сом</b>\n"
        if booster_account.balance_kz > 0:
            text += f"🇰🇿 <b>{booster_account.balance_kz:.2f} тенге</b>\n"  
        if booster_account.balance_ru > 0:
            text += f"🇷🇺 <b>{booster_account.balance_ru:.2f} руб.</b>\n"
        
        total_balance = await get_booster_total_balance_in_currency(user.id, user_currency)
        text += f"\n💎 <b>Общий баланс:</b> {total_balance:.2f} {user_currency}\n\n"
        text += "💡 <i>Средства начисляются по курсу валюты заказа</i>"
        
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=booster_balance_keyboard()
        )
