from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.database.crud import get_user_by_tg_id, get_user_orders, get_orders_count, get_order_by_id
from app.config import PAGE_SIZE
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "📦 Мои заказы")
async def show_my_orders(message: Message):
    """Показать заказы пользователя"""
    logger.info(f"Пользователь @{message.from_user.username} открыл свои заказы")
    
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Напишите /start для регистрации.")
        return
    
    orders = await get_user_orders(user.id, limit=PAGE_SIZE)
    total_orders = await get_orders_count(user.id)
    
    if not orders:
        await message.answer(
            "📦 <b>Ваши заказы</b>\n\n"
            "У вас пока нет заказов.\n"
            "Нажмите «🎮 Создать заказ» для создания первого заказа.",
            parse_mode="HTML"
        )
        return
    
    text = f"📦 <b>Ваши заказы</b> ({total_orders})\n\n"
    
    for order in orders:
        status_emoji = get_status_emoji(order.status)
        text += f"{status_emoji} <b>{order.order_id}</b>\n"
        text += f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"💰 {order.total_cost:.0f} {order.currency}\n"
        text += f"📊 {get_status_name(order.status)}\n\n"
    
    keyboard = create_orders_keyboard(orders, page=0, total_orders=total_orders)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data.startswith("order_detail:"))
async def show_order_detail(call: CallbackQuery):
    """Показать детали заказа"""
    order_id = call.data.split(":")[1]
    logger.info(f"Пользователь @{call.from_user.username} открыл детали заказа {order_id}")
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    # Проверяем, что заказ принадлежит пользователю
    user = await get_user_by_tg_id(call.from_user.id)
    if not user or order.user_id != user.id:
        await call.answer("Доступ запрещен!", show_alert=True)
        return
    
    text = format_order_details(order)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к заказам", callback_data="back_to_orders")]
        ]
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data == "back_to_orders")
async def back_to_orders(call: CallbackQuery):
    """Возврат к списку заказов"""
    logger.info(f"Пользователь @{call.from_user.username} вернулся к списку заказов")
    
    user = await get_user_by_tg_id(call.from_user.id)
    if not user:
        await call.answer("Профиль не найден!", show_alert=True)
        return
    
    orders = await get_user_orders(user.id, limit=PAGE_SIZE)
    total_orders = await get_orders_count(user.id)
    
    text = f"📦 <b>Ваши заказы</b> ({total_orders})\n\n"
    
    for order in orders:
        status_emoji = get_status_emoji(order.status)
        text += f"{status_emoji} <b>{order.order_id}</b>\n"
        text += f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"💰 {order.total_cost:.0f} {order.currency}\n"
        text += f"📊 {get_status_name(order.status)}\n\n"
    
    keyboard = create_orders_keyboard(orders, page=0, total_orders=total_orders)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data.startswith("orders_page:"))
async def orders_pagination(call: CallbackQuery):
    """Пагинация заказов"""
    page = int(call.data.split(":")[1])
    
    user = await get_user_by_tg_id(call.from_user.id)
    if not user:
        await call.answer("Профиль не найден!", show_alert=True)
        return
    
    orders = await get_user_orders(user.id, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    total_orders = await get_orders_count(user.id)
    
    text = f"📦 <b>Ваши заказы</b> ({total_orders})\n\n"
    
    for order in orders:
        status_emoji = get_status_emoji(order.status)
        text += f"{status_emoji} <b>{order.order_id}</b>\n"
        text += f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"💰 {order.total_cost:.0f} {order.currency}\n"
        text += f"📊 {get_status_name(order.status)}\n\n"
    
    keyboard = create_orders_keyboard(orders, page=page, total_orders=total_orders)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи для статуса"""
    status_emojis = {
        "pending": "🟡",
        "confirmed": "🟢",
        "in_progress": "🔵",
        "completed": "✅",
        "cancelled": "❌"
    }
    return status_emojis.get(status, "❓")

def get_status_name(status: str) -> str:
    """Возвращает название статуса"""
    status_names = {
        "pending": "Ожидает подтверждения",
        "confirmed": "Подтвержден",
        "in_progress": "В процессе",
        "completed": "Выполнен",
        "cancelled": "Отменен"
    }
    return status_names.get(status, "Неизвестен")

def create_orders_keyboard(orders, page: int, total_orders: int):
    """Создает клавиатуру для списка заказов"""
    keyboard = []
    
    # Кнопки для заказов
    for order in orders:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📋 {order.order_id}",
                callback_data=f"order_detail:{order.order_id}"
            )
        ])
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"orders_page:{page-1}"))
    
    if (page + 1) * PAGE_SIZE < total_orders:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"orders_page:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def format_order_details(order):
    """Форматирует детали заказа"""
    service_names = {
        "regular_boost": "Обычный буст",
        "hero_boost": "Буст персонажа",
        "coaching": "Гайд / обучение"
    }
    
    boost_names = {
        "account": "Через вход на аккаунт",
        "shared": "Совместный буст",
        "mmr": "Буст ММР",
        "winrate": "Буст винрейта"
    }
    
    text = f"📋 <b>Детали заказа {order.order_id}</b>\n\n"
    
    text += f"🎮 <b>Услуга:</b> {service_names.get(order.service_type)}\n"
    
    if order.boost_type:
        text += f"🔧 <b>Тип:</b> {boost_names.get(order.boost_type)}\n"
    
    if order.current_rank:
        text += f"📊 <b>Текущий ранг:</b> {order.current_rank}"
        if order.current_mythic_stars is not None:
            text += f" ({order.current_mythic_stars} ⭐)"
        text += "\n"
    
    if order.target_rank:
        text += f"🎯 <b>Желаемый ранг:</b> {order.target_rank}"
        if order.target_mythic_stars is not None:
            text += f" ({order.target_mythic_stars} ⭐)"
        text += "\n"
    
    if order.lane:
        text += f"🎮 <b>Лайн:</b> {order.lane}\n"
    
    if order.heroes_mains:
        text += f"🎯 <b>Мейны:</b> {order.heroes_mains}\n"
    
    if order.game_id:
        text += f"🆔 <b>Игровой ID:</b> {order.game_id}\n"
    
    if order.preferred_time:
        text += f"⏰ <b>Время:</b> {order.preferred_time}\n"
    
    if order.coaching_topic:
        text += f"📚 <b>Тема обучения:</b> {order.coaching_topic}\n"
    
    if order.coaching_hours:
        text += f"⏱️ <b>Часов:</b> {order.coaching_hours}\n"
    
    if order.contact_info:
        text += f"📞 <b>Контакты:</b> {order.contact_info}\n"
    
    if order.details:
        text += f"📝 <b>Детали:</b> {order.details}\n"
    
    text += f"\n💰 <b>Стоимость:</b> {order.total_cost:.0f} {order.currency}\n"
    text += f"📊 <b>Статус:</b> {get_status_name(order.status)}\n"
    text += f"📅 <b>Создан:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}"
    
    return text