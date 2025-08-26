from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from app.utils.roles import admin_only
from app.states.admin_states import AdminStates
from app.database.crud import (
    get_order_by_id, get_all_orders, update_order_status, assign_booster_to_order,
    get_active_boosters, get_user_by_id, update_user_balance_by_region,
    search_orders, count_orders_by_status, get_boosters, update_booster_balance
)
from app.keyboards.admin.order_management import (
    admin_order_details_keyboard, admin_boosters_list_keyboard, 
    admin_orders_list_keyboard, confirm_action_keyboard
)
import logging
from datetime import datetime

router = Router()
logger = logging.getLogger(__name__)

def get_currency_for_order(order, user=None):
    """Получает валюту для заказа, определяя её по региону пользователя если нужно"""
    currency = order.currency
    if not currency or currency == "None" or currency is None:
        if user and user.region:
            region_currencies = {
                "🇰🇬 КР": "сом",
                "🇰🇿 КЗ": "тенге", 
                "🇷🇺 РУ": "руб."
            }
            currency = region_currencies.get(user.region, "валюта")
        else:
            currency = "валюта"
    return currency

def get_currency_for_order(order, user=None):
    """Получает валюту для заказа, определяя её по региону пользователя если нужно"""
    currency = order.currency
    if not currency or currency == "None" or currency is None:
        if user and user.region:
            region_currencies = {
                "🇰🇬 КР": "сом",
                "🇰🇿 КЗ": "тенге", 
                "🇷🇺 РУ": "руб."
            }
            currency = region_currencies.get(user.region, "валюта")
        else:
            currency = "валюта"
    return currency

# === ОБРАБОТЧИК КНОПКИ "📦 ВСЕ ЗАКАЗЫ" ===

@router.message(F.text == "📦 Все заказы")
@admin_only
async def show_all_orders_button(message: Message):
    """Обработчик нажатия кнопки '📦 Все заказы' в админ-меню"""
    logger.info(f"Админ @{message.from_user.username} открыл список всех заказов")
    await show_orders_list(message, status_filter="all", page=0)

# === ОБРАБОТЧИК ВОЗВРАТА В ГЛАВНОЕ МЕНЮ ===

@router.callback_query(F.data == "admin_main_menu")
@admin_only
async def admin_main_menu_callback(call: CallbackQuery):
    """Возврат в главное админ-меню"""
    from app.keyboards.admin.admin_menu import admin_menu_keyboard
    logger.info(f"Админ @{call.from_user.username} вернулся в главное меню")
    await call.message.delete()
    await call.message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard())

# === ОБРАБОТЧИК СПИСКА ЗАКАЗОВ ===

@router.callback_query(F.data == "admin_orders_list")
@admin_only
async def admin_orders_list_callback(call: CallbackQuery):
    """Показать список всех заказов"""
    logger.info(f"Админ @{call.from_user.username} открыл список заказов")
    await show_orders_list(call, status_filter="all", page=0, edit_message=True)

# === ОБРАБОТЧИКИ УВЕДОМЛЕНИЙ О НОВЫХ ЗАКАЗАХ ===

# Убираем отдельную функцию принятия заказа - теперь заказ принимается автоматически при назначении бустера

@router.callback_query(F.data.startswith("admin_reject_order:"))
@admin_only
async def admin_reject_order(call: CallbackQuery):
    """Отклонение заказа админом"""
    order_id = call.data.split(":")[1]
    logger.info(f"Админ @{call.from_user.username} отклоняет заказ {order_id}")
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    if order.status != "pending":
        await call.answer("Заказ уже обработан!", show_alert=True)
        return
    
    # Получаем пользователя для определения валюты
    user = await get_user_by_id(order.user_id)
    currency = get_currency_for_order(order, user)
    
    await call.message.edit_text(
        f"❌ <b>Отклонение заказа {order_id}</b>\n\n"
        f"Вы уверены, что хотите отклонить этот заказ?\n"
        f"Клиенту будет возвращена полная стоимость: <b>{order.total_cost:.0f} {currency}</b>",
        parse_mode="HTML",
        reply_markup=confirm_action_keyboard("reject", order_id)
    )
    await call.answer()

@router.callback_query(F.data.startswith("admin_confirm_reject:"))
@admin_only
async def admin_confirm_reject_order(call: CallbackQuery):
    """Подтверждение отклонения заказа"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    # Отменяем заказ и возвращаем деньги
    await update_order_status(order_id, "cancelled")
    
    # Возвращаем деньги на баланс пользователя
    user = await get_user_by_id(order.user_id)
    if user:
        # Определяем поле баланса по региону заказа
        if "🇰🇬" in order.region or order.region == "KG":
            balance_field = "balance_kg"
        elif "🇰🇿" in order.region or order.region == "KZ":
            balance_field = "balance_kz"
        elif "🇷🇺" in order.region or order.region == "RU":
            balance_field = "balance_ru"
        else:
            # По умолчанию возвращаем в рублях
            balance_field = "balance_ru"
        
        await update_user_balance_by_region(user.id, balance_field, order.total_cost)
    
    # Получаем информацию о клиенте
    user = await get_user_by_id(order.user_id)
    currency = get_currency_for_order(order, user)
    
    await call.message.edit_text(
        f"❌ <b>Заказ {order_id} отклонен</b>\n\n"
        f"Деньги возвращены на баланс клиента: <b>{order.total_cost:.0f} {currency}</b>\n"
        f"Клиент уведомлен об отклонении.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗂️ Все заказы", callback_data="admin_orders_list")]
        ])
    )
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            user.tg_id,
            f"❌ <b>Ваш заказ {order_id} отклонен</b>\n\n"
            f"Деньги возвращены на ваш баланс: <b>{order.total_cost:.0f} {currency}</b>\n"
            f"Вы можете создать новый заказ в любое время.",
            parse_mode="HTML"
        )
        logger.info(f"Клиент {user.tg_id} уведомлен об отклонении заказа {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {user.tg_id}: {e}")
    
    logger.info(f"Админ @{call.from_user.username} отклонил заказ {order_id}, возвращено {order.total_cost} {currency}")
    await call.answer("Заказ отклонен, деньги возвращены!")

# === ДЕТАЛЬНЫЙ ПРОСМОТР ЗАКАЗА ===

@router.callback_query(F.data.startswith("admin_order_details:"))
@admin_only
async def admin_order_details(call: CallbackQuery):
    """Детальная информация о заказе"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    user = await get_user_by_id(order.user_id)
    
    # Формируем детальную информацию
    text = await format_order_details(order, user)
    
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_order_details_keyboard(order_id, order.status)
    )
    await call.answer()

async def format_order_details(order, user):
    """Форматирует детальную информацию о заказе"""
    
    # Статусы на русском
    status_names = {
        "pending": "⏳ Ожидает подтверждения",
        "confirmed": "✅ Подтвержден",
        "in_progress": "🚀 В работе",
        "paused": "⏸️ Приостановлен",
        "pending_review": "📋 Ожидает проверки",
        "completed": "✅ Завершен",
        "cancelled": "❌ Отменен"
    }
    
    # Типы услуг
    service_names = {
        "regular_boost": "🎮 Обычный буст",
        "hero_boost": "🎯 Буст персонажа",
        "coaching": "📚 Гайд / обучение"
    }
    
    # Типы буста
    boost_names = {
        "account": "🔐 Через вход на аккаунт",
        "shared": "🤝 Совместный буст",
        "mmr": "📊 Буст ММР",
        "winrate": "📈 Буст винрейта"
    }
    
    text = f"📋 <b>Заказ {order.order_id}</b>\n\n"
    
    # Статус и время
    text += f"📊 <b>Статус:</b> {status_names.get(order.status, order.status)}\n"
    text += f"📅 <b>Создан:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    # Информация о клиенте
    if user.username:
        text += f"👤 <b>Клиент:</b> @{user.username} (ID: {user.tg_id})\n"
    else:
        text += f"👤 <b>Клиент:</b> <a href='tg://user?id={user.tg_id}'>Связаться</a> (ID: {user.tg_id})\n"
    text += f"🌍 <b>Регион:</b> {user.region}\n\n"
    
    # Детали заказа
    text += f"🛒 <b>Услуга:</b> {service_names.get(order.service_type, 'Неизвестно')}\n"
    
    if order.service_type == "coaching":
        text += f"📚 <b>Тема:</b> {order.coaching_topic or 'Не указана'}\n"
        text += f"⏱️ <b>Часов:</b> {order.coaching_hours or 1}\n"
    else:
        text += f"🔧 <b>Тип:</b> {boost_names.get(order.boost_type, 'Неизвестно')}\n"
        
        # Ранги
        if order.current_rank == "Мифик":
            text += f"📊 <b>Текущий:</b> Мифик {order.current_mythic_stars or 0} ⭐\n"
        else:
            text += f"📊 <b>Текущий:</b> {order.current_rank}\n"
        
        if order.target_rank == "Мифик":
            text += f"🎯 <b>Желаемый:</b> Мифик {order.target_mythic_stars or 0} ⭐\n"
        else:
            text += f"🎯 <b>Желаемый:</b> {order.target_rank}\n"
        
        # Дополнительная информация
        if order.lane:
            text += f"🎮 <b>Лайн:</b> {order.lane}\n"
        if order.heroes_mains:
            text += f"🎭 <b>Мейны:</b> {order.heroes_mains}\n"
        if order.game_id:
            text += f"🆔 <b>Игровой ID:</b> {order.game_id}\n"
        if order.preferred_time:
            text += f"⏰ <b>Время:</b> {order.preferred_time}\n"
    
    # Контакты и детали
    if order.contact_info:
        text += f"📞 <b>Контакты:</b> {order.contact_info}\n"
    if order.details:
        text += f"📝 <b>Детали:</b> {order.details}\n"
    
    # Финансы
    # Определяем валюту по региону пользователя, если она не указана
    currency = get_currency_for_order(order, user)
    
    text += f"\n💰 <b>Стоимость:</b> {order.total_cost:.0f} {currency}\n"
    
    # Назначенный бустер
    if order.assigned_booster_id:
        booster = await get_user_by_id(order.assigned_booster_id)
        if booster:
            if booster.username:
                text += f"👨‍💼 <b>Бустер:</b> @{booster.username} (ID: {booster.tg_id})\n"
            else:
                text += f"👨‍💼 <b>Бустер:</b> <a href='tg://user?id={booster.tg_id}'>Связаться</a> (ID: {booster.tg_id})\n"
    
    return text

# === НАЗНАЧЕНИЕ БУСТЕРА ===

@router.callback_query(F.data.startswith("admin_assign_booster:"))
@admin_only
async def admin_assign_booster(call: CallbackQuery):
    """Показывает список бустеров для назначения"""
    order_id = call.data.split(":")[1]
    
    boosters = await get_active_boosters()
    
    if not boosters:
        await call.answer("Нет доступных бустеров!", show_alert=True)
        return
    
    await call.message.edit_text(
        f"👥 <b>Выбор бустера для заказа {order_id}</b>\n\n"
        f"Выберите бустера из списка:\n"
        f"🟢 - активен, 🔴 - неактивен",
        parse_mode="HTML",
        reply_markup=admin_boosters_list_keyboard(order_id, boosters)
    )
    await call.answer()

@router.callback_query(F.data.startswith("admin_select_booster:"))
@admin_only
async def admin_select_booster(call: CallbackQuery):
    """Назначает выбранного бустера на заказ"""
    parts = call.data.split(":")
    order_id = parts[1]
    booster_user_id = int(parts[2])
    
    logger.info(f"Админ @{call.from_user.username} назначает бустера {booster_user_id} на заказ {order_id}")
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    # Если заказ еще pending, меняем статус на confirmed при назначении бустера
    if order.status == "pending":
        await update_order_status(order_id, "confirmed")
    
    # Назначаем бустера
    order = await assign_booster_to_order(order_id, booster_user_id)
    if not order:
        await call.answer("Ошибка назначения бустера!", show_alert=True)
        return
    
    # Получаем информацию о бустере и клиенте
    booster = await get_user_by_id(booster_user_id)
    client = await get_user_by_id(order.user_id)
    
    if booster.username:
        booster_text = f"👨‍💼 <b>Бустер:</b> @{booster.username} (ID: {booster.tg_id})"
    else:
        booster_text = f"👨‍💼 <b>Бустер:</b> <a href='tg://user?id={booster.tg_id}'>Связаться</a> (ID: {booster.tg_id})"
    
    if client.username:
        client_text = f"👤 <b>Клиент:</b> @{client.username} (ID: {client.tg_id})"
    else:
        client_text = f"👤 <b>Клиент:</b> <a href='tg://user?id={client.tg_id}'>Связаться</a> (ID: {client.tg_id})"
    
    await call.message.edit_text(
        f"✅ <b>Бустер назначен!</b>\n\n"
        f"📋 <b>Заказ:</b> {order_id}\n"
        f"{booster_text}\n"
        f"{client_text}\n\n"
        f"Заказ подтвержден и назначен! Все участники уведомлены.",
        parse_mode="HTML",
        reply_markup=admin_order_details_keyboard(order_id, "confirmed")
    )
    
    # Уведомляем бустера
    try:
        currency = get_currency_for_order(order, client)
        
        # Формируем детальную информацию для бустера
        notification_text = f"🎯 <b>Вам назначен новый заказ!</b>\n\n"
        notification_text += f"📋 <b>Заказ:</b> {order_id}\n"
        if client.username:
            notification_text += f"👤 <b>Клиент:</b> @{client.username} (ID: {client.tg_id})\n"
        else:
            notification_text += f"👤 <b>Клиент:</b> <a href='tg://user?id={client.tg_id}'>Связаться</a> (ID: {client.tg_id})\n"
        notification_text += f"🌍 <b>Регион:</b> {client.region}\n"
        
        # Получаем процент дохода бустера из настроек
        from app.utils.settings import get_booster_income_percent
        try:
            booster_percent = await get_booster_income_percent()
        except:
            booster_percent = 70  # По умолчанию 70%
        
        booster_income = order.total_cost * (booster_percent / 100)
        notification_text += f"💰 <b>Ваш доход:</b> {booster_income:.0f} {currency} ({booster_percent}%)\n\n"
        
        # Добавляем краткую информацию о заказе
        if order.service_type == "coaching":
            notification_text += f"📚 <b>Услуга:</b> Гайд / обучение\n"
            if order.coaching_topic:
                notification_text += f"📖 <b>Тема:</b> {order.coaching_topic}\n"
            if order.coaching_hours:
                notification_text += f"⏱️ <b>Часов:</b> {order.coaching_hours}\n"
        else:
            notification_text += f"🎮 <b>Услуга:</b> Буст ранга\n"
            if order.current_rank:
                notification_text += f"📊 <b>Текущий ранг:</b> {order.current_rank}\n"
            if order.target_rank:
                notification_text += f"🎯 <b>Целевой ранг:</b> {order.target_rank}\n"
        
        notification_text += f"\n💡 <i>Нажмите кнопку ниже для просмотра полных деталей заказа</i>"
        
        await call.bot.send_message(
            booster.tg_id,
            notification_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Подробнее о заказе", callback_data=f"booster_order_details:{order_id}")],
                [InlineKeyboardButton(text="📦 Мои заказы", callback_data="booster_refresh_orders")]
            ])
        )
        logger.info(f"Бустер {booster.tg_id} уведомлен о назначении на заказ {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить бустера {booster.tg_id}: {e}")
    
    # Уведомляем клиента
    try:
        booster_contact = f"@{booster.username}" if booster.username else f"<a href='tg://user?id={booster.tg_id}'>Связаться с исполнителем</a>"
        
        await call.bot.send_message(
            client.tg_id,
            f"✅ <b>Ваш заказ {order_id} принят в работу!</b>\n\n"
            f"👨‍💼 <b>Назначен исполнитель:</b> {booster_contact}\n\n"
            f"Исполнитель свяжется с вами в ближайшее время для начала работы.",
            parse_mode="HTML"
        )
        logger.info(f"Клиент {client.tg_id} уведомлен о принятии заказа и назначении бустера {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    await call.answer("Бустер назначен, заказ подтвержден!")

# === УПРАВЛЕНИЕ СТАТУСАМИ ЗАКАЗОВ ===

@router.callback_query(F.data.startswith("admin_start_order:"))
@admin_only
async def admin_start_order(call: CallbackQuery):
    """Запуск заказа в работу"""
    order_id = call.data.split(":")[1]
    
    await update_order_status(order_id, "in_progress")
    
    order = await get_order_by_id(order_id)
    client = await get_user_by_id(order.user_id)
    
    await call.message.edit_text(
        f"🚀 <b>Заказ {order_id} запущен в работу!</b>\n\n"
        f"Статус изменен на: <b>В работе</b>\n"
        f"Клиент уведомлен о начале выполнения.",
        parse_mode="HTML",
        reply_markup=admin_order_details_keyboard(order_id, "in_progress")
    )
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"🚀 <b>Ваш заказ {order_id} взят в работу!</b>\n\n"
            f"Исполнитель начал выполнение заказа.\n"
            f"Следите за прогрессом в разделе \"Мои заказы\".",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    logger.info(f"Админ @{call.from_user.username} запустил заказ {order_id} в работу")
    await call.answer("Заказ запущен в работу!")

@router.callback_query(F.data.startswith("admin_complete_order:"))
@admin_only
async def admin_complete_order(call: CallbackQuery):
    """Завершение заказа"""
    order_id = call.data.split(":")[1]
    
    await update_order_status(order_id, "completed")
    
    order = await get_order_by_id(order_id)
    client = await get_user_by_id(order.user_id)
    
    await call.message.edit_text(
        f"✅ <b>Заказ {order_id} завершен!</b>\n\n"
        f"Статус изменен на: <b>Завершен</b>\n"
        f"Клиент уведомлен о завершении.",
        parse_mode="HTML",
        reply_markup=admin_order_details_keyboard(order_id, "completed")
    )
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"🎉 <b>Ваш заказ {order_id} завершен!</b>\n\n"
            f"Спасибо за использование наших услуг!\n"
            f"Вы можете оставить отзыв или создать новый заказ.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    logger.info(f"Админ @{call.from_user.username} завершил заказ {order_id}")
    await call.answer("Заказ завершен!")

# === СПИСОК ЗАКАЗОВ ===

@router.callback_query(F.data == "admin_orders_list")
@admin_only
async def admin_orders_list(call: CallbackQuery):
    """Показывает список всех заказов"""
    await show_orders_list(call, status_filter="all", page=0)

@router.callback_query(F.data.startswith("admin_orders_filter:"))
@admin_only
async def admin_orders_filter(call: CallbackQuery):
    """Фильтрация заказов по статусу"""
    parts = call.data.split(":")
    status_filter = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    
    logger.info(f"Админ @{call.from_user.username} применил фильтр: {status_filter}")
    await show_orders_list(call, status_filter, page, edit_message=True)

@router.callback_query(F.data.startswith("admin_orders_page:"))
@admin_only
async def admin_orders_page(call: CallbackQuery):
    """Навигация по страницам заказов"""
    parts = call.data.split(":")
    status_filter = parts[1]
    page = int(parts[2])
    
    logger.info(f"Админ @{call.from_user.username} перешел на страницу {page + 1} с фильтром {status_filter}")
    await show_orders_list(call, status_filter, page, edit_message=True)

async def show_orders_list(event, status_filter: str = "all", page: int = 0, edit_message: bool = False):
    """Отображает список заказов с пагинацией"""
    per_page = 5  # Уменьшаем количество заказов на страницу
    offset = page * per_page
    
    orders = await get_all_orders(status_filter, per_page + 1, offset)  # +1 для проверки наличия следующей страницы
    
    # Статистика
    total_count = await count_orders_by_status()
    pending_count = await count_orders_by_status("pending")
    
    text = f"📋 <b>Управление заказами</b>\n\n"
    text += f"📊 <b>Статистика:</b>\n"
    text += f"• Всего заказов: {total_count}\n"
    text += f"• Ожидающих: {pending_count}\n\n"
    
    status_names = {
        "all": "Все заказы",
        "pending": "Ожидающие подтверждения", 
        "confirmed": "Подтвержденные",
        "in_progress": "В работе",
        "paused": "Приостановленные",
        "pending_review": "Ожидают проверки",
        "completed": "Завершенные",
        "cancelled": "Отмененные"
    }
    
    text += f"📂 <b>Фильтр:</b> {status_names.get(status_filter, status_filter)}\n"
    text += f"📄 <b>Страница:</b> {page + 1}\n\n"
    
    display_orders = []  # Инициализируем переменную
    
    if not orders:
        text += "❌ Заказов не найдено."
    else:
        # Показываем заказы (максимум per_page)
        display_orders = orders[:per_page]
        
        for i, order in enumerate(display_orders, 1):
            user =await get_user_by_id(order.user_id)
            currency = get_currency_for_order(order, user)
            status_emoji = {
                "pending": "⏳",
                "confirmed": "✅",
                "in_progress": "🚀",
                "paused": "⏸️",
                "pending_review": "📋",
                "completed": "✅",
                "cancelled": "❌"
            }.get(order.status, "❓")
            
            text += f"{page * per_page + i}. {status_emoji} <b>{order.order_id}</b>\n"
            if user.username:
                text += f"   👤 @{user.username} (ID: {user.tg_id})\n"
            else:
                text += f"   👤 <a href='tg://user?id={user.tg_id}'>Связаться</a> (ID: {user.tg_id})\n"
            text += f"   💰 {order.total_cost:.0f} {currency}\n"
            text += f"   📅 {order.created_at.strftime('%d.%m %H:%M')}\n\n"
    
    # Создаем базовую клавиатуру
    keyboard = []
    
    # Фильтры по статусу
    status_filters = [
        ("📋 Все", "all"),
        ("⏳ Ожидающие", "pending"), 
        ("✅ Подтвержденные", "confirmed"),
        ("🚀 В работе", "in_progress"),
        ("⏸️ Приостановленные", "paused"),
        ("📋 На проверке", "pending_review"),
        ("✅ Завершенные", "completed"),
        ("❌ Отмененные", "cancelled")
    ]
    
    # Разбиваем фильтры на строки по 3
    for i in range(0, len(status_filters), 3):
        row = []
        for j in range(i, min(i + 3, len(status_filters))):
            text_filter, status = status_filters[j]
            emoji = "🔹" if status == status_filter else ""
            button_text = f"{emoji}{text_filter}"
            row.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f"admin_orders_filter:{status}:0"
            ))
        keyboard.append(row)
    
    # Добавляем кнопки для заказов
    if display_orders:
        for order in display_orders:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📋 {order.order_id}", 
                    callback_data=f"admin_order_details:{order.order_id}"
                )
            ])
    
    # Навигация
    has_next = len(orders) > per_page
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_orders_page:{status_filter}:{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_search_order"))
    if has_next:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_orders_page:{status_filter}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Возврат в главное меню
    keyboard.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправка или редактирование сообщения
    if edit_message and hasattr(event, 'message'):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        if hasattr(event, 'answer'):
            await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=reply_markup)

# === ДОПОЛНИТЕЛЬНЫЕ ОБРАБОТЧИКИ КНОПОК ===

@router.callback_query(F.data.startswith("admin_pause_order:"))
@admin_only
async def admin_pause_order(call: CallbackQuery):
    """Приостановка заказа"""
    order_id = call.data.split(":")[1]
    
    await update_order_status(order_id, "paused")
    
    order = await get_order_by_id(order_id)
    client = await get_user_by_id(order.user_id)
    
    await call.message.edit_text(
        f"⏸️ <b>Заказ {order_id} приостановлен</b>\n\n"
        f"Статус изменен на: <b>Приостановлен</b>\n"
        f"Клиент уведомлен о приостановке.",
        parse_mode="HTML",
        reply_markup=admin_order_details_keyboard(order_id, "paused")
    )
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"⏸️ <b>Ваш заказ {order_id} временно приостановлен</b>\n\n"
            f"Работа по заказу будет возобновлена в ближайшее время.\n"
            f"При возникновении вопросов обратитесь в поддержку.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    logger.info(f"Админ @{call.from_user.username} приостановил заказ {order_id}")
    await call.answer("Заказ приостановлен!")

@router.callback_query(F.data.startswith("admin_resume_order:"))
@admin_only
async def admin_resume_order(call: CallbackQuery):
    """Возобновление приостановленного заказа"""
    order_id = call.data.split(":")[1]
    
    await update_order_status(order_id, "in_progress")
    
    order = await get_order_by_id(order_id)
    client = await get_user_by_id(order.user_id)
    
    await call.message.edit_text(
        f"▶️ <b>Заказ {order_id} возобновлен</b>\n\n"
        f"Статус изменен на: <b>В работе</b>\n"
        f"Клиент уведомлен о возобновлении работы.",
        parse_mode="HTML",
        reply_markup=admin_order_details_keyboard(order_id, "in_progress")
    )
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"▶️ <b>Работа по заказу {order_id} возобновлена!</b>\n\n"
            f"Исполнитель продолжает выполнение заказа.\n"
            f"Следите за прогрессом в разделе \"Мои заказы\".",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    logger.info(f"Админ @{call.from_user.username} возобновил заказ {order_id}")
    await call.answer("Заказ возобновлен!")

@router.callback_query(F.data.startswith("admin_client_profile:"))
@admin_only
async def admin_client_profile(call: CallbackQuery):
    """Просмотр профиля клиента"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    client = await get_user_by_id(order.user_id)
    if not client:
        await call.answer("Клиент не найден!", show_alert=True)
        return
    
    # Формируем информацию о клиенте
    text = f"👤 <b>Профиль клиента</b>\n\n"
    text += f"🆔 <b>ID:</b> {client.id}\n"
    text += f"📱 <b>Telegram ID:</b> {client.tg_id}\n"
    if client.username:
        text += f"👤 <b>Username:</b> @{client.username}\n"
    else:
        text += f"👤 <b>Username:</b> не указан\n"
        text += f"📞 <b>Связь:</b> <a href='tg://user?id={client.tg_id}'>Написать в Telegram</a>\n"
    text += f"🌍 <b>Регион:</b> {client.region}\n"
    text += f"📅 <b>Регистрация:</b> {client.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    # Балансы
    text += f"💰 <b>Балансы:</b>\n"
    text += f"🇰🇬 КГ: {client.balance_kg:.0f} сом\n"
    text += f"🇰🇿 КЗ: {client.balance_kz:.0f} тенге\n"
    text += f"🇷🇺 РУ: {client.balance_ru:.0f} руб.\n\n"
    
    text += f"👥 <b>Роль:</b> {client.role}\n"
    # У User нет поля status, это есть только у BoosterAccount
    text += f"📊 <b>Статус:</b> Активен"  # Всегда активен для обычных пользователей
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 К заказу", callback_data=f"admin_order_details:{order_id}")
        ]
    ])
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data == "admin_search_order")
@admin_only
async def admin_search_order(call: CallbackQuery, state: FSMContext):
    """Поиск заказа по ID"""
    await call.message.edit_text(
        "🔍 <b>Поиск заказа</b>\n\n"
        "Введите ID заказа для поиска:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_orders_list")]
        ])
    )
    await state.set_state(AdminStates.searching_order)
    await call.answer()

@router.message(AdminStates.searching_order)
@admin_only
async def process_search_order(message: Message, state: FSMContext):
    """Обработка поиска заказа"""
    order_id = message.text.strip()
    
    order = await get_order_by_id(order_id)
    if not order:
        await message.answer(
            f"❌ Заказ с ID '{order_id}' не найден.\n\n"
            f"Попробуйте ввести другой ID:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К списку заказов", callback_data="admin_orders_list")]
            ])
        )
        return
    
    # Показываем найденный заказ
    user = await get_user_by_id(order.user_id)
    text = await format_order_details(order, user)
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=admin_order_details_keyboard(order_id, order.status)
    )
    
    await state.clear()
    logger.info(f"Админ @{message.from_user.username} нашел заказ {order_id}")

# === ПРОВЕРКА ЗАВЕРШЕНИЯ ЗАКАЗОВ ===

@router.callback_query(F.data.startswith("admin_approve_completion:"))
@admin_only
async def admin_approve_completion(call: CallbackQuery):
    """Одобрение завершения заказа админом"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    if order.status != "pending_review":
        await call.answer("Заказ не ожидает проверки!", show_alert=True)
        return
    
    # Обновляем статус заказа
    await update_order_status(order_id, "completed")
    
    # Получаем информацию о бустере и клиенте
    booster = await get_user_by_id(order.assigned_booster_id)
    client = await get_user_by_id(order.user_id)
    currency = get_currency_for_order(order, client)
    
    # Получаем процент дохода бустера из настроек
    from app.utils.settings import get_booster_income_percent
    try:
        booster_percent = await get_booster_income_percent()
    except:
        booster_percent = 70  # По умолчанию 70%
    
    # Начисляем бустеру указанный процент от стоимости заказа
    booster_amount = order.total_cost * (booster_percent / 100)
    
    # Определяем валюту выплаты
    order_currency = currency  # Валюта заказа
    booster_region_currencies = {
        "🇰🇬 КР": "сом",
        "🇰🇿 КЗ": "тенге", 
        "🇷🇺 РУ": "руб."
    }
    booster_currency = booster_region_currencies.get(booster.region, "руб.")
    
    # Если валюты отличаются, конвертируем
    final_amount = booster_amount
    conversion_note = ""
    
    if order_currency != booster_currency:
        try:
            from app.utils.currency_converter import convert_booster_balance
            final_amount = await convert_booster_balance(booster_amount, order_currency, booster_currency)
            conversion_note = f"\n💱 Конвертировано: {booster_amount:.0f} {order_currency} → {final_amount:.0f} {booster_currency}"
        except Exception as e:
            logger.error(f"Ошибка конвертации валюты: {e}")
            # В случае ошибки используем валюту заказа
            booster_currency = order_currency
            final_amount = booster_amount
    
    await update_booster_balance(order.assigned_booster_id, final_amount, booster_currency)
    
    # TODO: Начисляем клиенту кешбэк (настройка в админ-панели)
    # cashback_percent = await get_setting("cashback_percent", 5)  # 5% по умолчанию
    # cashback_amount = order.total_cost * (cashback_percent / 100)
    # await update_user_balance_by_region(client.id, get_balance_field(client.region), cashback_amount)
    
    # Форматируем строки пользователей
    booster_str = f"@{booster.username}" if booster.username else f'<a href="tg://user?id={booster.tg_id}">Связаться</a>'
    client_str = f"@{client.username}" if client.username else f'<a href="tg://user?id={client.tg_id}">Связаться</a>'
    
    await call.message.edit_caption(
        caption=f"✅ <b>Заказ {order_id} одобрен!</b>\n\n"
               f"Бустер: {booster_str} ({booster.region})\n"
               f"Клиент: {client_str}\n"
               f"Стоимость: {order.total_cost:.0f} {currency}\n\n"
               f"💰 Бустеру начислено: {final_amount:.0f} {booster_currency} ({booster_percent}%)"
               f"{conversion_note}\n"
               f"🎁 Клиенту начислен кешбэк\n\n"
               f"Все участники уведомлены!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Детали заказа", callback_data=f"admin_order_details:{order_id}")]
        ])
    )
    
    # Уведомляем бустера
    try:
        await call.bot.send_message(
            booster.tg_id,
            f"🎉 <b>Ваш заказ {order_id} одобрен!</b>\n\n"
            f"Заказ успешно завершен и проверен администрацией.\n"
            f"💰 Вам начислено: <b>{booster_amount:.0f} {currency}</b> ({booster_percent}%)\n\n"
            f"Спасибо за качественную работу!",
            parse_mode="HTML"
        )
        logger.info(f"Бустер {booster.tg_id} уведомлен об одобрении заказа {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить бустера {booster.tg_id}: {e}")
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"🎉 <b>Ваш заказ {order_id} выполнен!</b>\n\n"
            f"Заказ успешно завершен и проверен.\n"
            f"🎁 Вам начислен кешбэк за заказ.\n\n"
            f"Спасибо за использование наших услуг!\n"
            f"Будем рады видеть вас снова!",
            parse_mode="HTML"
        )
        logger.info(f"Клиент {client.tg_id} уведомлен о завершении заказа {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    logger.info(f"Админ @{call.from_user.username} одобрил завершение заказа {order_id}")
    await call.answer("Заказ одобрен!")

# === ОБРАБОТЧИКИ НАВИГАЦИИ ===

@router.callback_query(F.data.startswith("admin_boosters_page:"))
@admin_only
async def admin_boosters_page(call: CallbackQuery):
    """Навигация по страницам бустеров"""
    parts = call.data.split(":")
    order_id = parts[1]
    page = int(parts[2])
    
    boosters = await get_active_boosters()
    
    await call.message.edit_text(
        f"👥 <b>Выбор бустера для заказа {order_id}</b>\n\n"
        f"Выберите бустера из списка:\n"
        f"🟢 - активен, 🔴 - неактивен",
        parse_mode="HTML",
        reply_markup=admin_boosters_list_keyboard(order_id, boosters, page)
    )
    await call.answer()

# === ПОДТВЕРЖДЕНИЕ ЗАВЕРШЕНИЯ ЗАКАЗА ===

@router.callback_query(F.data.startswith("admin_reject_completion:"))
@admin_only
async def admin_reject_order_completion(call: CallbackQuery):
    """Отклонение завершения заказа админом"""
    order_id = call.data.split(":")[1]
    logger.info(f"Админ @{call.from_user.username} отклоняет завершение заказа {order_id}")
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    if order.status != "pending_review":
        await call.answer("Заказ не на проверке!", show_alert=True)
        return
    
    # Возвращаем статус заказа в работу
    await update_order_status(order_id, "in_progress")
    
    # Получаем информацию о клиенте и бустере
    client = await get_user_by_id(order.user_id)
    booster = await get_user_by_id(order.assigned_booster_id)
    
    # Форматируем строки пользователей  
    client_str = f"@{client.username}" if client.username else f'<a href="tg://user?id={client.tg_id}">Связаться</a>'
    booster_str = f"@{booster.username}" if booster.username else f'<a href="tg://user?id={booster.tg_id}">Связаться</a>'
    
    await call.message.edit_text(
        f"❌ <b>Завершение отклонено!</b>\n\n"
        f"🆔 <b>Заказ:</b> {order_id}\n"
        f"👤 <b>Клиент:</b> {client_str}\n"
        f"🎯 <b>Бустер:</b> {booster_str}\n\n"
        f"Заказ возвращен в работу.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Управление заказами", callback_data="admin_orders_list")]
        ])
    )
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"⚠️ <b>Заказ возвращен в работу</b>\n\n"
            f"По заказу {order_id} требуются доработки.\n"
            f"Исполнитель продолжит работу над заказом.\n\n"
            f"Следите за прогрессом в разделе \"Мои заказы\".",
            parse_mode="HTML"
        )
        logger.info(f"Клиент {client.tg_id} уведомлен о возврате заказа {order_id} в работу")
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    # Уведомляем бустера
    try:
        await call.bot.send_message(
            booster.tg_id,
            f"⚠️ <b>Заказ требует доработки</b>\n\n"
            f"Ваше выполнение заказа {order_id} требует доработки.\n"
            f"Пожалуйста, продолжите работу над заказом.\n\n"
            f"Свяжитесь с администратором для уточнений.",
            parse_mode="HTML"
        )
        logger.info(f"Бустер {booster.tg_id} уведомлен о возврате заказа {order_id} в работу")
    except Exception as e:
        logger.warning(f"Не удалось уведомить бустера {booster.tg_id}: {e}")
    
    logger.info(f"Завершение заказа {order_id} отклонено админом @{call.from_user.username}")
    await call.answer("Заказ возвращен в работу!")
