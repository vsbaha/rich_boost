from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from app.utils.roles import booster_only
from app.states.booster_states import BoosterStates
from app.database.crud import (
    get_order_by_id, get_orders_by_booster, update_order_status, 
    get_user_by_id, get_booster_account, get_user_by_tg_id, get_users_by_role
)
from app.keyboards.booster.order_management import (
    booster_order_details_keyboard, booster_work_progress_keyboard,
    booster_complete_order_keyboard, my_orders_list_keyboard
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

async def send_admin_order_completion_notification(bot, order, booster_user, client, proof_message=None):
    """Отправка уведомления админу о завершении заказа бустером"""
    
    # Получаем всех админов из базы данных
    admins = await get_users_by_role("admin")
    
    if not admins:
        logger.warning("Не найдено ни одного администратора в базе данных")
        return
    
    # Формируем текст уведомления
    service_names = {
        "regular_boost": "🎮 Обычный буст",
        "hero_boost": "🎯 Буст персонажа", 
        "coaching": "📚 Гайд / обучение"
    }
    
    boost_names = {
        "account": "🔐 Через вход на аккаунт",
        "shared": "🤝 Совместный буст",
        "mmr": "📊 Буст ММР",
        "winrate": "📈 Буст винрейта"
    }
    
    text = f"✅ <b>ЗАКАЗ ЗАВЕРШЕН БУСТЕРОМ!</b>\n\n"
    text += f"🆔 <b>ID заказа:</b> <code>{order.order_id}</code>\n"
    if client.username:
        text += f"👤 <b>Клиент:</b> @{client.username} ({client.tg_id})\n"
    else:
        text += f"👤 <b>Клиент:</b> <a href='tg://user?id={client.tg_id}'>Связаться</a> ({client.tg_id})\n"
    if booster_user.username:
        text += f"🎯 <b>Бустер:</b> @{booster_user.username} ({booster_user.tg_id})\n"
    else:
        text += f"🎯 <b>Бустер:</b> <a href='tg://user?id={booster_user.tg_id}'>Связаться</a> ({booster_user.tg_id})\n"
    text += f"🌍 <b>Регион:</b> {client.region}\n\n"
    
    text += f"🛒 <b>Услуга:</b> {service_names.get(order.service_type, 'Неизвестно')}\n"
    
    if order.service_type == "coaching":
        text += f"📚 <b>Тема:</b> {order.coaching_topic or 'Не указана'}\n"
        text += f"⏱️ <b>Часов:</b> {order.coaching_hours or 1}\n"
    else:
        text += f"🔧 <b>Тип:</b> {boost_names.get(order.boost_type, 'Неизвестно')}\n"
        
        if order.current_rank == "Мифик":
            text += f"📊 <b>Текущий:</b> Мифик {order.current_mythic_stars or 0} ⭐\n"
        else:
            text += f"📊 <b>Текущий:</b> {order.current_rank}\n"
        
        if order.target_rank == "Мифик":
            text += f"🎯 <b>Цель:</b> Мифик {order.target_mythic_stars or 0} ⭐\n"
        else:
            text += f"🎯 <b>Цель:</b> {order.target_rank}\n"
    
    currency = get_currency_for_order(order, client)
    
    # Импортируем функцию для получения процента дохода бустера
    from app.utils.settings import get_booster_income_percent
    booster_percent = await get_booster_income_percent()
    booster_income = order.total_cost * (booster_percent / 100)
    
    text += f"\n💰 <b>Стоимость:</b> {order.total_cost:.0f} {currency}\n"
    text += f"💳 <b>Доход бустера:</b> {booster_income:.0f} {currency} ({booster_percent}%)\n"
    text += f"📅 <b>Завершен:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
    text += f"📋 <b>Статус:</b> Ожидает проверки и подтверждения"
    
    # Создаем клавиатуру для админа
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_approve_completion:{order.order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_completion:{order.order_id}")
        ],
        [
            InlineKeyboardButton(text="📋 Детали заказа", callback_data=f"admin_order_details:{order.order_id}")
        ]
    ])
    
    # Отправляем всем админам из базы данных
    sent_count = 0
    for admin in admins:
        try:
            # Сначала отправляем основное уведомление
            await bot.send_message(
                chat_id=admin.tg_id,
                text=text,
                parse_mode="HTML",
                reply_markup=admin_keyboard
            )
            
            # Если есть доказательство (фото/медиа/текст), пересылаем его
            if proof_message:
                proof_text = f"📸 <b>Доказательство выполнения заказа {order.order_id}:</b>"
                
                # Проверяем тип контента и пересылаем соответственно
                if proof_message.photo:
                    await bot.send_photo(
                        chat_id=admin.tg_id,
                        photo=proof_message.photo[-1].file_id,
                        caption=proof_text + (f"\n\n💬 <b>Комментарий:</b> {proof_message.caption}" if proof_message.caption else ""),
                        parse_mode="HTML"
                    )
                elif proof_message.video:
                    await bot.send_video(
                        chat_id=admin.tg_id,
                        video=proof_message.video.file_id,
                        caption=proof_text + (f"\n\n💬 <b>Комментарий:</b> {proof_message.caption}" if proof_message.caption else ""),
                        parse_mode="HTML"
                    )
                elif proof_message.document:
                    await bot.send_document(
                        chat_id=admin.tg_id,
                        document=proof_message.document.file_id,
                        caption=proof_text + (f"\n\n💬 <b>Комментарий:</b> {proof_message.caption}" if proof_message.caption else ""),
                        parse_mode="HTML"
                    )
                elif proof_message.text:
                    await bot.send_message(
                        chat_id=admin.tg_id,
                        text=proof_text + f"\n\n💬 <b>Текст доказательства:</b>\n{proof_message.text}",
                        parse_mode="HTML"
                    )
            
            logger.info(f"Уведомление о завершении заказа {order.order_id} отправлено админу @{admin.username} ({admin.tg_id})")
            sent_count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу @{admin.username} ({admin.tg_id}): {e}")
    
    logger.info(f"Уведомление о завершении заказа {order.order_id} отправлено {sent_count} из {len(admins)} админов")

# === ПРОСМОТР НАЗНАЧЕННЫХ ЗАКАЗОВ ===

@router.message(F.text == "📦 Посмотреть заказы")
@booster_only
async def show_booster_orders(message: Message):
    """Показывает активные заказы назначенные бустеру"""
    # Получаем аккаунт бустера
    booster_account = await get_booster_account(message.from_user.id)
    if not booster_account:
        await message.answer("❌ Аккаунт бустера не найден!")
        return
    
    # Получаем user_id по tg_id
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден!")
        return
    
    # Получаем заказы бустера - используем user.id из базы данных
    orders = await get_orders_by_booster(user.id)
    
    logger.info(f"Бустер {message.from_user.id} (user_id={user.id}) запросил заказы. Найдено: {len(orders) if orders else 0} заказов")
    
    if not orders:
        await message.answer(
            "📦 <b>Мои заказы</b>\n\n"
            "У вас пока нет назначенных заказов.\n"
            "Ожидайте назначения новых заказов от администрации.",
            parse_mode="HTML"
        )
        return
    
    # Показываем активные заказы по умолчанию
    await show_filtered_orders(message, orders, show_active_only=True, page=0, edit_message=False)

async def show_filtered_orders(message_or_call, orders, show_active_only=True, page=0, edit_message=True):
    """Показывает отфильтрованный список заказов"""
    # Фильтруем заказы
    if show_active_only:
        filtered_orders = [o for o in orders if o.status in ["confirmed", "in_progress", "pending_review"]]
        filter_name = "активные"
    else:
        filtered_orders = orders
        filter_name = "все"
    
    # Группируем заказы по статусам для статистики
    pending_orders = [o for o in filtered_orders if o.status == "confirmed"]
    in_progress_orders = [o for o in filtered_orders if o.status == "in_progress"]
    pending_review_orders = [o for o in filtered_orders if o.status == "pending_review"]
    completed_orders = [o for o in filtered_orders if o.status == "completed"]
    
    text = f"📦 <b>Мои заказы ({filter_name})</b>\n\n"
    
    if filtered_orders:
        text += f"Всего {filter_name}: <b>{len(filtered_orders)}</b>\n\n"
        
        status_text = ""
        if pending_orders:
            status_text += f"⏳ <b>Ожидают начала:</b> {len(pending_orders)}\n"
        if in_progress_orders:
            status_text += f"🚀 <b>В работе:</b> {len(in_progress_orders)}\n"
        if pending_review_orders:
            status_text += f"📋 <b>На проверке:</b> {len(pending_review_orders)}\n"
        if completed_orders and not show_active_only:
            status_text += f"✅ <b>Завершенных:</b> {len(completed_orders)}\n"
        
        if status_text:
            text += f"{status_text}\n"
            
        text += "Выберите заказ для работы:"
    else:
        if show_active_only:
            text += "У вас нет активных заказов.\n"
            text += "Используйте кнопку ниже, чтобы посмотреть все заказы."
        else:
            text += "У вас пока нет заказов.\n"
            text += "Ожидайте назначения новых заказов от администрации."
    
    keyboard = my_orders_list_keyboard(orders, show_active_only, page)
    
    if edit_message and hasattr(message_or_call, 'message'):
        try:
            await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            # Если редактирование не удалось (например, контент не изменился), отправляем новое сообщение
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            await message_or_call.message.delete()
            await message_or_call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message_or_call.answer(text, parse_mode="HTML", reply_markup=keyboard)

# === ОБНОВЛЕНИЕ СПИСКА ЗАКАЗОВ ===

@router.callback_query(F.data == "booster_refresh_orders")
@booster_only
async def booster_refresh_orders(call: CallbackQuery):
    """Обновляет список заказов бустера"""
    # Получаем аккаунт бустера
    booster_account = await get_booster_account(call.from_user.id)
    if not booster_account:
        await call.answer("❌ Аккаунт бустера не найден!", show_alert=True)
        return
    
    # Получаем user_id по tg_id
    user = await get_user_by_tg_id(call.from_user.id)
    if not user:
        await call.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    # Получаем заказы бустера - используем user.id из базы данных
    orders = await get_orders_by_booster(user.id)
    
    if not orders:
        await call.message.edit_text(
            "📦 <b>Мои заказы</b>\n\n"
            "У вас пока нет назначенных заказов.\n"
            "Ожидайте назначения новых заказов от администрации.",
            parse_mode="HTML"
        )
        await call.answer("Список обновлен!")
        return
    
    # Показываем активные заказы по умолчанию
    await show_filtered_orders(call, orders, show_active_only=True, page=0, edit_message=True)
    await call.answer("Список заказов обновлен!")

# === ФИЛЬТРАЦИЯ И ПАГИНАЦИЯ ЗАКАЗОВ ===

@router.callback_query(F.data.startswith("booster_orders_filter:"))
@booster_only
async def filter_booster_orders(call: CallbackQuery):
    """Фильтрация заказов бустера"""
    _, filter_type, page_str = call.data.split(":")
    page = int(page_str)
    
    # Получаем user_id по tg_id
    user = await get_user_by_tg_id(call.from_user.id)
    if not user:
        await call.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    # Получаем заказы бустера
    orders = await get_orders_by_booster(user.id)
    
    show_active_only = filter_type == "active"
    await show_filtered_orders(call, orders, show_active_only, page, edit_message=True)
    await call.answer()

@router.callback_query(F.data.startswith("booster_orders_page:"))
@booster_only
async def paginate_booster_orders(call: CallbackQuery):
    """Пагинация заказов бустера"""
    _, show_active_str, page_str = call.data.split(":")
    show_active_only = show_active_str == "True"
    page = int(page_str)
    
    # Получаем user_id по tg_id
    user = await get_user_by_tg_id(call.from_user.id)
    if not user:
        await call.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    # Получаем заказы бустера
    orders = await get_orders_by_booster(user.id)
    
    await show_filtered_orders(call, orders, show_active_only, page, edit_message=True)
    await call.answer()

# === ДЕТАЛЬНЫЙ ПРОСМОТР ЗАКАЗА ===

@router.callback_query(F.data.startswith("booster_order_details:"))
@booster_only
async def booster_order_details(call: CallbackQuery):
    """Детальная информация о заказе для бустера"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    # Проверяем, что заказ назначен этому бустеру - сравниваем с user_id из БД
    booster_account = await get_booster_account(call.from_user.id)
    user = await get_user_by_tg_id(call.from_user.id)
    if not booster_account or not user or order.assigned_booster_id != user.id:
        await call.answer("Этот заказ не назначен вам!", show_alert=True)
        return
    
    client = await get_user_by_id(order.user_id)
    text = await format_booster_order_details(order, client)
    
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=booster_order_details_keyboard(order_id, order.status)
    )
    await call.answer()

async def format_booster_order_details(order, client):
    """Форматирует детальную информацию о заказе для бустера"""
    
    # Статусы на русском
    status_names = {
        "confirmed": "✅ Подтвержден",
        "in_progress": "🚀 В работе",
        "paused": "⏸️ Приостановлен",
        "completed": "✅ Завершен"
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
    
    # Статус
    text += f"📊 <b>Статус:</b> {status_names.get(order.status, order.status)}\n"
    text += f"📅 <b>Создан:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    # Информация о клиенте
    if client.username:
        text += f"👤 <b>Клиент:</b> @{client.username}\n"
    else:
        text += f"👤 <b>Клиент:</b> <a href='tg://user?id={client.tg_id}'>Связаться</a>\n"
    text += f"📱 <b>Telegram ID:</b> {client.tg_id}\n"
    text += f"🌍 <b>Регион:</b> {client.region}\n\n"
    
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
            text += f"🎯 <b>Цель:</b> Мифик {order.target_mythic_stars or 0} ⭐\n"
        else:
            text += f"🎯 <b>Цель:</b> {order.target_rank}\n"
        
        # Дополнительная информация
        if order.lane:
            text += f"🎮 <b>Лайн:</b> {order.lane}\n"
        if order.heroes_mains:
            text += f"🎭 <b>Мейны:</b> {order.heroes_mains}\n"
        if order.game_id:
            text += f"🆔 <b>Игровой ID:</b> {order.game_id}\n"
        
        # Данные для входа - показываем всегда, даже если не указаны
        text += f"👤 <b>Логин:</b> {order.game_login or 'Не указан'}\n"
        text += f"🔑 <b>Пароль:</b> <code>{order.game_password or 'Не указан'}</code>\n"
        
        if order.preferred_time:
            text += f"⏰ <b>Время:</b> {order.preferred_time}\n"
    
    # Контакты и детали
    if order.contact_info:
        text += f"📞 <b>Контакты:</b> {order.contact_info}\n"
    if order.details:
        text += f"📝 <b>Детали:</b> {order.details}\n"
    
    # Финансы
    currency = get_currency_for_order(order, client)
    
    # Получаем процент дохода бустера из настроек
    from app.utils.settings import get_booster_income_percent
    try:
        booster_percent = await get_booster_income_percent()
    except:
        booster_percent = 70  # По умолчанию 70%
    
    booster_income = order.total_cost * (booster_percent / 100)
    text += f"\n💰 <b>Ваш доход:</b> {booster_income:.0f} {currency} ({booster_percent}%)\n"
    
    return text

# === НАЧАЛО РАБОТЫ ===

@router.callback_query(F.data.startswith("booster_start_work:"))
@booster_only
async def booster_start_work(call: CallbackQuery):
    """Начало работы над заказом"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    # Проверяем, что заказ назначен этому бустеру - сравниваем с user_id из БД
    booster_account = await get_booster_account(call.from_user.id)
    user = await get_user_by_tg_id(call.from_user.id)
    if not booster_account or not user or order.assigned_booster_id != user.id:
        await call.answer("Этот заказ не назначен вам!", show_alert=True)
        return
    
    if order.status != "confirmed":
        await call.answer("Заказ нельзя взять в работу в текущем статусе!", show_alert=True)
        return
    
    # Обновляем статус заказа
    await update_order_status(order_id, "in_progress")
    
    client = await get_user_by_id(order.user_id)
    
    await call.message.edit_text(
        f"🚀 <b>Работа начата!</b>\n\n"
        f"Заказ {order_id} взят в работу.\n"
        f"Клиент уведомлен о начале выполнения.\n\n"
        f"Удачи в выполнении заказа!",
        parse_mode="HTML",
        reply_markup=booster_order_details_keyboard(order_id, "in_progress")
    )
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"🚀 <b>Работа началась!</b>\n\n"
            f"Ваш заказ {order_id} взят в работу исполнителем.\n"
            f"Следите за прогрессом в разделе \"Мои заказы\".",
            parse_mode="HTML"
        )
        logger.info(f"Клиент {client.tg_id} уведомлен о начале работы над заказом {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    logger.info(f"Бустер @{call.from_user.username} начал работу над заказом {order_id}")
    await call.answer("Работа началась!")

# === УПРАВЛЕНИЕ АККАУНТОМ ===

@router.callback_query(F.data.startswith("booster_take_account:"))
@booster_only
async def booster_take_account(call: CallbackQuery):
    """Уведомление клиента о том, что бустер займет аккаунт"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    # Проверяем, что заказ назначен этому бустеру - сравниваем с user_id из БД
    booster_account = await get_booster_account(call.from_user.id)
    user = await get_user_by_tg_id(call.from_user.id)
    if not booster_account or not user or order.assigned_booster_id != user.id:
        await call.answer("Этот заказ не назначен вам!", show_alert=True)
        return
    
    if order.status != "in_progress":
        await call.answer("Аккаунт можно занять только во время выполнения заказа!", show_alert=True)
        return
    
    client = await get_user_by_id(order.user_id)
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"🔒 <b>Аккаунт занят!</b>\n\n"
            f"Исполнитель заказа {order_id} зашел на ваш аккаунт для выполнения буста.\n"
            f"Пожалуйста, не входите в игру до завершения работы.\n\n"
            f"Следите за прогрессом в разделе \"Мои заказы\".",
            parse_mode="HTML"
        )
        logger.info(f"Клиент {client.tg_id} уведомлен о занятии аккаунта для заказа {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    await call.message.edit_text(
        f"🔒 <b>Аккаунт занят!</b>\n\n"
        f"Клиент уведомлен о том, что вы зашли на аккаунт.\n"
        f"Можете приступать к работе.\n\n"
        f"💡 <b>Данные для входа:</b>\n"
        f"🆔 <b>ID:</b> {order.game_id or 'Не указан'}\n"
        f"👤 <b>Логин:</b> {order.game_login or 'Не указан'}\n"  
        f"🔑 <b>Пароль:</b> <code>{order.game_password or 'Не указан'}</code>",
        parse_mode="HTML",
        reply_markup=booster_work_progress_keyboard(order_id, account_taken=True, status=order.status)
    )
    
    logger.info(f"Бустер @{call.from_user.username} занял аккаунт для заказа {order_id}")
    await call.answer("Аккаунт занят! Клиент уведомлен.")

@router.callback_query(F.data.startswith("booster_leave_account:"))
@booster_only
async def booster_leave_account(call: CallbackQuery):
    """Уведомление клиента о том, что бустер покинул аккаунт"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    # Проверяем, что заказ назначен этому бустеру - сравниваем с user_id из БД
    booster_account = await get_booster_account(call.from_user.id)
    user = await get_user_by_tg_id(call.from_user.id)
    if not booster_account or not user or order.assigned_booster_id != user.id:
        await call.answer("Этот заказ не назначен вам!", show_alert=True)
        return
    
    client = await get_user_by_id(order.user_id)
    
    # Уведомляем клиента
    try:
        await call.bot.send_message(
            client.tg_id,
            f"🔓 <b>Аккаунт свободен!</b>\n\n"
            f"Исполнитель заказа {order_id} покинул ваш аккаунт.\n"
            f"Теперь вы можете войти в игру.\n\n"
            f"Работа над заказом продолжается.",
            parse_mode="HTML"
        )
        logger.info(f"Клиент {client.tg_id} уведомлен об освобождении аккаунта для заказа {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    await call.message.edit_text(
        f"🔓 <b>Аккаунт освобожден!</b>\n\n"
        f"Клиент уведомлен о том, что вы покинули аккаунт.\n"
        f"Он может входить в игру.",
        parse_mode="HTML",
        reply_markup=booster_work_progress_keyboard(order_id, account_taken=False, status=order.status)
    )
    
    logger.info(f"Бустер @{call.from_user.username} покинул аккаунт для заказа {order_id}")
    await call.answer("Аккаунт освобожден! Клиент уведомлен.")

# === ЗАВЕРШЕНИЕ ЗАКАЗА ===

@router.callback_query(F.data.startswith("booster_complete_order:"))
@booster_only
async def booster_complete_order(call: CallbackQuery, state: FSMContext):
    """Завершение заказа бустером"""
    order_id = call.data.split(":")[1]
    
    order = await get_order_by_id(order_id)
    if not order:
        await call.answer("Заказ не найден!", show_alert=True)
        return
    
    # Проверяем, что заказ назначен этому бустеру - сравниваем с user_id из БД
    booster_account = await get_booster_account(call.from_user.id)
    user = await get_user_by_tg_id(call.from_user.id)
    if not booster_account or not user or order.assigned_booster_id != user.id:
        await call.answer("Этот заказ не назначен вам!", show_alert=True)
        return
    
    if order.status != "in_progress":
        await call.answer("Заказ нельзя завершить в текущем статусе!", show_alert=True)
        return
    
    # Сохраняем ID заказа в состоянии
    await state.update_data(order_id=order_id)
    await state.set_state(BoosterStates.sending_completion_proof)
    
    await call.message.edit_text(
        f"✅ <b>Завершение заказа {order_id}</b>\n\n"
        f"Пожалуйста, отправьте доказательство выполнения заказа:\n"
        f"📸 <b>Скриншот</b> результата\n"
        f"🎥 <b>Видео</b> с процессом/результатом\n"
        f"📄 <b>Текстовое описание</b> выполненной работы\n"
        f"📎 <b>Документ</b> с отчетом\n\n"
        f"После отправки доказательства заказ будет отправлен на проверку администратору.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к заказу", callback_data=f"booster_order_details:{order_id}")]
        ])
    )
    
    await call.answer()

@router.message(BoosterStates.sending_completion_proof)
@booster_only
async def process_completion_proof(message: Message, state: FSMContext):
    """Обработка доказательства выполнения заказа"""
    data = await state.get_data()
    order_id = data.get("order_id")
    
    if not order_id:
        await message.answer("❌ Ошибка: заказ не найден!")
        await state.clear()
        return
    
    order = await get_order_by_id(order_id)
    if not order:
        await message.answer("❌ Заказ не найден!")
        await state.clear()
        return
    
    # Обновляем статус заказа на "ожидает проверки"
    await update_order_status(order_id, "pending_review")
    
    client = await get_user_by_id(order.user_id)
    booster_user = await get_user_by_tg_id(message.from_user.id)
    
    await message.answer(
        f"✅ <b>Доказательство получено!</b>\n\n"
        f"Заказ {order_id} отправлен на проверку администратору.\n"
        f"Ожидайте подтверждения завершения.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Мои заказы", callback_data="booster_refresh_orders")]
        ])
    )
    
    # Уведомляем клиента
    try:
        await message.bot.send_message(
            client.tg_id,
            f"📋 <b>Заказ на проверке!</b>\n\n"
            f"Исполнитель отправил доказательства выполнения заказа {order_id}.\n"
            f"Ожидайте проверки и подтверждения от администратора.",
            parse_mode="HTML"
        )
        logger.info(f"Клиент {client.tg_id} уведомлен о завершении заказа {order_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить клиента {client.tg_id}: {e}")
    
    # Отправляем уведомление админам о завершении заказа с доказательствами
    try:
        await send_admin_order_completion_notification(message.bot, order, booster_user, client, message)
        logger.info(f"Админы уведомлены о завершении заказа {order_id}")
    except Exception as e:
        logger.error(f"Ошибка уведомления админов о завершении заказа {order_id}: {e}")
    
    logger.info(f"Бустер @{message.from_user.username} завершил заказ {order_id}")
    await state.clear()
