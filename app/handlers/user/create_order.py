from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from app.states.user_states import OrderStates
from app.keyboards.user.order_keyboards import (
    service_catalog_keyboard, regular_boost_type_keyboard, hero_boost_type_keyboard,
    main_ranks_keyboard, rank_gradations_keyboard, target_main_ranks_keyboard, 
    target_rank_gradations_keyboard, lanes_keyboard, back_keyboard, confirm_order_keyboard,
    edit_order_keyboard
)
from app.config import MAIN_RANKS, RANK_GRADATIONS, RANKS
from app.database.crud import get_user_by_tg_id, create_order, get_user_by_id, get_users_by_role, update_user_balance_by_region, apply_user_discount, use_user_bonus
from app.utils.price_calculator import (
    calculate_regular_rank_cost, calculate_mythic_cost, calculate_total_order_cost
)
import logging
import uuid

router = Router()
logger = logging.getLogger(__name__)

async def delete_message_safe(message: Message):
    """Безопасное удаление сообщения"""
    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение: {e}")

async def delete_bot_message_safe(bot: Bot, chat_id: int, message_id: int):
    """Безопасное удаление сообщения бота"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение бота: {e}")

def get_balance_field_from_region(region: str) -> str:
    """Определяет поле баланса по региону"""
    if "🇰🇬" in region or region == "KG":
        return "balance_kg"
    elif "🇰🇿" in region or region == "KZ":
        return "balance_kz"
    elif "🇷🇺" in region or region == "RU":
        return "balance_ru"
    else:
        # По умолчанию КГ если регион не определен
        return "balance_kg"

def get_user_balance_by_region(user, region: str) -> float:
    """Получает баланс пользователя по региону"""
    balance_field = get_balance_field_from_region(region)
    return float(getattr(user, balance_field, 0) or 0)

async def calculate_order_cost(data):
    """Рассчитывает базовую стоимость заказа"""
    service_type = data.get("service_type")
    region = data.get("region")
    
    # Валидация региона
    if not region:
        logger.error("Регион не указан в данных заказа")
        return 0
    
    if service_type == "coaching":
        from app.utils.settings import SettingsManager
        coaching_prices = await SettingsManager.get_setting("COACHING_PRICES")
        
        # Проверяем, есть ли цены для данного региона
        if region not in coaching_prices:
            logger.error(f"Цены обучения не найдены для региона: {region}")
            return 0
            
        hours = data.get("coaching_hours", 1)
        return coaching_prices[region] * hours
    
    current_rank = data.get("current_rank")
    target_rank = data.get("target_rank")
    
    if not current_rank or not target_rank:
        logger.error(f"Не указаны ранги: current={current_rank}, target={target_rank}")
        return 0
    
    total_cost = 0
    
    try:
        # Буст обычных рангов
        if current_rank != "Мифик" or target_rank != "Мифик":
            if current_rank != "Мифик" and target_rank != "Мифик":
                # Обычный ранг -> обычный ранг
                total_cost += await calculate_regular_rank_cost(current_rank, target_rank, region)
            elif current_rank != "Мифик" and target_rank == "Мифик":
                # Обычный ранг -> Мифик
                total_cost += await calculate_regular_rank_cost(current_rank, "Мифик", region)
                target_stars = data.get("target_mythic_stars", 0)
                if target_stars > 0:
                    total_cost += await calculate_mythic_cost(0, target_stars, region)
        
        # Буст внутри Мифик
        if current_rank == "Мифик" and target_rank == "Мифик":
            current_stars = data.get("current_mythic_stars", 0)
            target_stars = data.get("target_mythic_stars", 0)
            total_cost += await calculate_mythic_cost(current_stars, target_stars, region)
        
    except Exception as e:
        logger.error(f"Ошибка расчета стоимости заказа: {e}")
        return 0
    
    return total_cost

async def format_order_summary(data, total_cost, currency):
    """Форматирует итоговый заказ для отображения"""
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
    
    text = "📋 <b>Итоговый заказ</b>\n\n"
    text += f"🛒 <b>Услуга:</b> {service_names.get(data.get('service_type'), 'Неизвестно')}\n"
    
    if data.get("service_type") == "coaching":
        text += f"📚 <b>Тема:</b> {data.get('coaching_topic', 'Не указана')}\n"
        text += f"⏱️ <b>Часов:</b> {data.get('coaching_hours', 1)}\n"
    else:
        text += f"🔧 <b>Тип:</b> {boost_names.get(data.get('boost_type'), 'Неизвестно')}\n"
        
        current_rank = data.get("current_rank")
        target_rank = data.get("target_rank")
        
        if current_rank == "Мифик":
            current_stars = data.get("current_mythic_stars", 0)
            text += f"📊 <b>Текущий ранг:</b> Мифик {current_stars} ⭐\n"
        else:
            text += f"📊 <b>Текущий ранг:</b> {current_rank}\n"
        
        if target_rank == "Мифик":
            target_stars = data.get("target_mythic_stars", 0)
            text += f"🎯 <b>Желаемый ранг:</b> Мифик {target_stars} ⭐\n"
        else:
            text += f"🎯 <b>Желаемый ранг:</b> {target_rank}\n"
        
        if data.get("lane"):
            text += f"🎮 <b>Лайн:</b> {data.get('lane')}\n"
        if data.get("heroes_mains"):
            text += f"🎭 <b>Мейны:</b> {data.get('heroes_mains')}\n"
        if data.get("game_id"):
            text += f"🆔 <b>Игровой ID:</b> {data.get('game_id')}\n"
        if data.get("preferred_time"):
            text += f"⏰ <b>Время:</b> {data.get('preferred_time')}\n"
    
    if data.get("contact_info"):
        text += f"📞 <b>Контакты:</b> {data.get('contact_info')}\n"
    if data.get("details"):
        text += f"📝 <b>Детали:</b> {data.get('details')}\n"
    
    text += f"\n💰 <b>Стоимость:</b> {total_cost:.0f} {currency}"
    
    return text

async def show_order_summary(message: Message, state: FSMContext):
    """Показ итогового заказа для подтверждения"""
    data = await state.get_data()
    
    # Проверяем наличие обязательных данных
    if not data.get("region"):
        await message.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Регион не определен. Начните создание заказа заново.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Рассчитываем стоимость
    base_cost = await calculate_order_cost(data)
    
    if base_cost <= 0:
        await message.answer(
            "❌ <b>Ошибка расчета стоимости</b>\n\n"
            "Проверьте данные заказа и попробуйте снова.",
            parse_mode="HTML"
        )
        return
    
    total_cost, currency = await calculate_total_order_cost(base_cost, data.get("boost_type"), data.get("region"))
    
    await state.update_data(base_cost=base_cost, total_cost=total_cost, currency=currency)
    
    # Формируем текст заказа
    summary_text = await format_order_summary(data, total_cost, currency)
    
    sent_message = await message.answer(
        summary_text,
        parse_mode="HTML",
        reply_markup=confirm_order_keyboard()
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.confirming_order)

@router.message(F.text == "🎮 Создать заказ")
async def start_order_creation(message: Message, state: FSMContext):
    """Начало создания заказа"""
    logger.info(f"Пользователь @{message.from_user.username} начал создание заказа")
    
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Напишите /start для регистрации.")
        return
    
    # Логируем полученные данные для отладки
    logger.info(f"Пользователь найден: ID={user.id}, region={user.region}, balance_kg={user.balance_kg}, balance_kz={user.balance_kz}, balance_ru={user.balance_ru}")
    
    # Сохраняем пользователя в состоянии
    await state.update_data(user_id=user.id, region=user.region)
    
    sent_message = await message.answer(
        "🛒 <b>Каталог услуг</b>\n\n"
        "Выберите тип услуги:",
        parse_mode="HTML",
        reply_markup=service_catalog_keyboard()
    )
    
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.choosing_service)

@router.callback_query(F.data.startswith("service:"))
async def handle_service_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора типа услуги"""
    service_type = call.data.split(":")[1]
    logger.info(f"Пользователь @{call.from_user.username} выбрал услугу: {service_type}")
    
    await state.update_data(service_type=service_type)
    
    if service_type == "regular_boost":
        await call.message.edit_text(
            "🎮 <b>Обычный буст</b>\n\n"
            "Выберите тип буста:",
            parse_mode="HTML",
            reply_markup=regular_boost_type_keyboard()
        )
        await state.set_state(OrderStates.choosing_boost_type)
    
    elif service_type == "hero_boost":
        await call.message.edit_text(
            "🎯 <b>Буст на конкретного персонажа</b>\n\n"
            "Выберите тип буста:",
            parse_mode="HTML",
            reply_markup=hero_boost_type_keyboard()
        )
        await state.set_state(OrderStates.choosing_boost_type)
    
    elif service_type == "coaching":
        await call.message.edit_text(
            "📚 <b>Гайд / обучение</b>\n\n"
            "Введите количество часов обучения:",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_catalog")
        )
        await state.set_state(OrderStates.entering_coaching_hours)
    
    await call.answer()

@router.callback_query(F.data.startswith("boost_type:"))
async def handle_boost_type_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора типа буста"""
    boost_type = call.data.split(":")[1]
    logger.info(f"Пользователь @{call.from_user.username} выбрал тип буста: {boost_type}")
    
    await state.update_data(boost_type=boost_type)
    
    await call.message.edit_text(
        "📊 <b>Выбор текущего ранга</b>\n\n"
        "Выберите ваш текущий ранг:",
        parse_mode="HTML",
        reply_markup=main_ranks_keyboard()
    )
    await state.set_state(OrderStates.choosing_main_rank)
    await call.answer()

@router.callback_query(F.data.startswith("main_rank:"))
async def handle_main_rank_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора основного ранга"""
    main_rank = call.data.split(":")[1]
    logger.info(f"Пользователь @{call.from_user.username} выбрал основной ранг: {main_rank}")
    
    await state.update_data(current_main_rank=main_rank)
    
    # Если выбран Мифик, сразу переходим к вводу звезд
    if main_rank == "Мифик":
        await state.update_data(current_rank="Мифик")
        await call.message.edit_text(
            "⭐ <b>Мифик ранг</b>\n\n"
            "Введите количество ваших текущих звезд (0-1000):",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_main_ranks")
        )
        await state.set_state(OrderStates.entering_current_mythic)
    else:
        # Показываем градации для других рангов
        await call.message.edit_text(
            f"📊 <b>{main_rank}</b>\n\n"
            "Выберите точный ранг:",
            parse_mode="HTML",
            reply_markup=rank_gradations_keyboard(main_rank)
        )
        await state.set_state(OrderStates.choosing_rank_gradation)
    
    await call.answer()

@router.callback_query(F.data.startswith("rank:"))
async def handle_rank_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора конкретного ранга"""
    rank = call.data.split(":")[1]
    current_state = await state.get_state()
    data = await state.get_data()
    
    if current_state == OrderStates.choosing_rank_gradation:
        logger.info(f"Пользователь @{call.from_user.username} выбрал текущий ранг: {rank}")
        await state.update_data(current_rank=rank)
        
        # Проверяем, находимся ли мы в режиме редактирования
        if data.get("total_cost") and data.get("target_rank"):
            # Это редактирование - возвращаемся к сводке
            await show_order_summary_callback(call, state)
            return
        
        # Переходим к выбору целевого основного ранга
        await call.message.edit_text(
            "🎯 <b>Выбор желаемого ранга</b>\n\n"
            "Выберите желаемый ранг:",
            parse_mode="HTML",
            reply_markup=target_main_ranks_keyboard(rank)
        )
        await state.set_state(OrderStates.choosing_target_main_rank)
    
    elif current_state == OrderStates.choosing_target_gradation:
        logger.info(f"Пользователь @{call.from_user.username} выбрал желаемый ранг: {rank}")
        await state.update_data(target_rank=rank)
        
        # Проверяем, находимся ли мы в режиме редактирования
        if data.get("total_cost"):
            # Возвращаемся к сводке
            await show_order_summary_callback(call, state)
            return
        
        # Переходим к следующему этапу
        await proceed_to_next_step(call, state)
    
    await call.answer()

async def show_order_summary_callback(call: CallbackQuery, state: FSMContext):
    """Показ итогового заказа для подтверждения (для callback)"""
    data = await state.get_data()
    
    # Проверяем наличие обязательных данных
    if not data.get("region"):
        await call.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Регион не определен. Начните создание заказа заново.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Рассчитываем стоимость
    base_cost = await calculate_order_cost(data)
    
    if base_cost <= 0:
        await call.message.edit_text(
            "❌ <b>Ошибка расчета стоимости</b>\n\n"
            "Проверьте данные заказа и попробуйте снова.",
            parse_mode="HTML"
        )
        return
    
    total_cost, currency = await calculate_total_order_cost(base_cost, data.get("boost_type"), data.get("region"))
    
    await state.update_data(base_cost=base_cost, total_cost=total_cost, currency=currency)
    
    # Формируем текст заказа
    summary_text = await format_order_summary(data, total_cost, currency)
    
    await call.message.edit_text(
        summary_text,
        parse_mode="HTML",
        reply_markup=confirm_order_keyboard()
    )
    await state.set_state(OrderStates.confirming_order)
    await call.answer()
    
@router.message(OrderStates.entering_current_mythic)
async def handle_current_mythic_stars(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода текущих звезд Mythic"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    try:
        stars = int(message.text)
        if stars < 0 or stars > 1000:
            sent_message = await message.answer(
                "❌ Введите корректное количество звезд (0-1000).",
                reply_markup=back_keyboard("back_to_main_ranks")
            )
            await state.update_data(last_bot_message_id=sent_message.message_id)
            return
        
        logger.info(f"Пользователь @{message.from_user.username} ввел текущие Mythic звезды: {stars}")
        await state.update_data(current_mythic_stars=stars)
        
        # Проверяем, находимся ли мы в режиме редактирования
        if data.get("total_cost"):
            # Это редактирование - возвращаемся к сводке
            await show_order_summary(message, state)
            return
        
        # Обычный процесс создания - продолжаем
        current_rank = data.get("current_rank")
        sent_message = await message.answer(
            "🎯 <b>Выбор желаемого ранга</b>\n\n"
            "Выберите желаемый ранг:",
            parse_mode="HTML",
            reply_markup=target_main_ranks_keyboard(current_rank)
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state(OrderStates.choosing_target_main_rank)
        
    except ValueError:
        sent_message = await message.answer(
            "❌ Введите корректное число.",
            reply_markup=back_keyboard("back_to_main_ranks")
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)

@router.message(OrderStates.entering_target_mythic)
async def handle_target_mythic_stars(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода желаемых звезд Mythic"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    try:
        stars = int(message.text)
        if stars < 0 or stars > 1000:
            sent_message = await message.answer(
                "❌ Введите корректное количество звезд (0-1000).",
                reply_markup=back_keyboard("back_to_target_main_ranks")
            )
            await state.update_data(last_bot_message_id=sent_message.message_id)
            return
        
        # Валидация звезд Mythic
        current_stars = data.get("current_mythic_stars", 0)
        
        if stars <= current_stars:
            sent_message = await message.answer(
                f"❌ <b>Ошибка!</b>\n\n"
                f"Желаемое количество звезд ({stars}) должно быть больше текущего ({current_stars}).\n"
                f"Введите корректное количество звезд:",
                parse_mode="HTML",
                reply_markup=back_keyboard("back_to_target_main_ranks")
            )
            await state.update_data(last_bot_message_id=sent_message.message_id)
            return
        
        logger.info(f"Пользователь @{message.from_user.username} ввел желаемые Mythic звезды: {stars}")
        await state.update_data(target_mythic_stars=stars)
        
        # Проверяем, находимся ли мы в режиме редактирования
        if data.get("total_cost"):
            # Возвращаемся к сводке
            await show_order_summary(message, state)
            return
        
        # Иначе продолжаем обычный процесс
        await proceed_to_next_step(message, state)
        
    except ValueError:
        sent_message = await message.answer(
            "❌ Введите корректное число.",
            reply_markup=back_keyboard("back_to_target_main_ranks")
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)

@router.message(OrderStates.entering_coaching_hours)
async def handle_coaching_hours(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода часов обучения"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    try:
        hours = int(message.text)
        if hours <= 0:
            sent_message = await message.answer(
                "❌ Введите корректное количество часов (больше 0).",
                reply_markup=back_keyboard("back_to_catalog")
            )
            await state.update_data(last_bot_message_id=sent_message.message_id)
            return
        
        logger.info(f"Пользователь @{message.from_user.username} выбрал {hours} часов обучения")
        await state.update_data(coaching_hours=hours)
        
        # Проверяем, находимся ли мы в режиме редактирования
        if data.get("total_cost"):
            # Возвращаемся к сводке
            await show_order_summary(message, state)
            return
        
        # Иначе продолжаем обычный процесс
        sent_message = await message.answer(
            "📚 <b>Тема обучения</b>\n\n"
            "Что именно хотите изучить? (герой, роль, сборка, тактика и т.д.):",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_catalog")
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state(OrderStates.entering_coaching_topic)
        
    except ValueError:
        sent_message = await message.answer(
            "❌ Введите корректное число.",
            reply_markup=back_keyboard("back_to_catalog")
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)

@router.message(OrderStates.entering_coaching_topic)
async def handle_coaching_topic(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода темы обучения"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    logger.info(f"Пользователь @{message.from_user.username} ввел тему обучения")
    await state.update_data(coaching_topic=message.text)
    
    # Проверяем, находимся ли мы в режиме редактирования
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary(message, state)
        return
    
    # Иначе продолжаем обычный процесс
    sent_message = await message.answer(
        "📞 <b>Контакты</b>\n\n"
        "Введите ваши контакты для связи (Discord, Telegram и т.д.):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_coaching_topic")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_contact_info)

@router.message(OrderStates.entering_game_id)
async def handle_game_id(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода игрового ID"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    logger.info(f"Пользователь @{message.from_user.username} ввел игровой ID: {message.text}")
    await state.update_data(game_id=message.text)
    
    # Проверяем, находимся ли мы в режиме редактирования
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary(message, state)
        return
    
    # Иначе продолжаем обычный процесс
    sent_message = await message.answer(
        "🎮 <b>Выбор лайна</b>\n\n"
        "Выберите ваш предпочитаемый лайн:",
        parse_mode="HTML",
        reply_markup=lanes_keyboard()
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.choosing_lane)
    
@router.callback_query(F.data.startswith("lane:"))
async def handle_lane_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора лайна"""
    lane = call.data.split(":")[1]
    logger.info(f"Пользователь @{call.from_user.username} выбрал лайн: {lane}")
    
    await state.update_data(lane=lane)
    
    # Проверяем, находимся ли мы в режиме редактирования
    data = await state.get_data()
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary_callback(call, state)
        return
    
    # Иначе продолжаем обычный процесс
    await call.message.edit_text(
        "🎯 <b>Мейны</b>\n\n"
        "Напишите ваших основных героев (мейнов):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_game_id")
    )
    await state.set_state(OrderStates.entering_heroes)
    await call.answer()

@router.message(OrderStates.entering_heroes)
async def handle_heroes(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода мейнов"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    logger.info(f"Пользователь @{message.from_user.username} ввел мейнов: {message.text}")
    await state.update_data(heroes_mains=message.text)
    
    # Проверяем, находимся ли мы в режиме редактирования
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary(message, state)
        return
    
    # Иначе продолжаем обычный процесс
    sent_message = await message.answer(
        "⏰ <b>Удобное время</b>\n\n"
        "Введите удобное время для совместной игры:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_heroes")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_preferred_time)

@router.message(OrderStates.entering_preferred_time)
async def handle_preferred_time(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода удобного времени"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    logger.info(f"Пользователь @{message.from_user.username} ввел удобное время")
    await state.update_data(preferred_time=message.text)
    
    # Проверяем, находимся ли мы в режиме редактирования
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary(message, state)
        return
    
    # Иначе продолжаем обычный процесс
    sent_message = await message.answer(
        "📝 <b>Дополнительные детали</b>\n\n"
        "Введите дополнительные пожелания или детали заказа (или напишите 'нет'):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_preferred_time")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_details)

@router.message(OrderStates.entering_contact_info)
async def handle_contact_info(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода контактов"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    logger.info(f"Пользователь @{message.from_user.username} ввел контакты")
    await state.update_data(contact_info=message.text)
    
    # Проверяем, находимся ли мы в режиме редактирования
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary(message, state)
        return
    
    # Иначе продолжаем обычный процесс
    sent_message = await message.answer(
        "📝 <b>Дополнительные детали</b>\n\n"
        "Введите дополнительные пожелания или детали заказа (или напишите 'нет'):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_contact_info")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_details)

@router.message(OrderStates.entering_account_data)
async def handle_account_data(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода данных аккаунта"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    # Парсим данные аккаунта
    account_text = message.text.strip()
    game_login = None
    game_password = None
    
    # Пытаемся найти логин и пароль в тексте
    lines = account_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.lower().startswith('логин:') or line.lower().startswith('login:'):
            game_login = line.split(':', 1)[1].strip()
        elif line.lower().startswith('пароль:') or line.lower().startswith('password:'):
            game_password = line.split(':', 1)[1].strip()
    
    # Проверяем, что данные введены корректно
    if not game_login or not game_password:
        sent_message = await message.answer(
            "❌ <b>Неверный формат данных!</b>\n\n"
            "Пожалуйста, введите данные в правильном формате:\n"
            "<code>Логин: ваш_логин\n"
            "Пароль: ваш_пароль</code>\n\n"
            "Попробуйте еще раз:",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_target_gradation")
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)
        return
    
    logger.info(f"Пользователь @{message.from_user.username} ввел данные аккаунта: логин={game_login}")
    await state.update_data(
        account_data=account_text,
        game_login=game_login,
        game_password=game_password
    )
    
    # Проверяем, находимся ли мы в режиме редактирования
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary(message, state)
        return
    
    # Иначе продолжаем обычный процесс
    sent_message = await message.answer(
        "📝 <b>Дополнительные детали</b>\n\n"
        "Введите дополнительные пожелания или детали заказа (или напишите 'нет'):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_account_data")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_details)

# === НОВЫЕ ОБРАБОТЧИКИ ДЛЯ РАЗДЕЛЬНОГО ВВОДА ЛОГИНА И ПАРОЛЯ ===

@router.message(OrderStates.entering_game_login)
async def handle_game_login(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода логина аккаунта"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    game_login = message.text.strip()
    
    # Проверяем, что логин не пустой
    if not game_login:
        sent_message = await message.answer(
            "❌ <b>Логин не может быть пустым!</b>\n\n"
            "Пожалуйста, введите логин от вашего игрового аккаунта:",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_target_gradation")
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)
        return
    
    logger.info(f"Пользователь @{message.from_user.username} ввел логин: {game_login}")
    await state.update_data(game_login=game_login)
    
    # Проверяем, находимся ли мы в режиме редактирования
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary(message, state)
        return
    
    # Переходим к вводу пароля
    sent_message = await message.answer(
        "🔐 <b>Пароль аккаунта</b>\n\n"
        "Введите пароль от вашего игрового аккаунта:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_game_login")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_game_password)

@router.message(OrderStates.entering_game_password)
async def handle_game_password(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода пароля аккаунта"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    game_password = message.text.strip()
    
    # Проверяем, что пароль не пустой
    if not game_password:
        sent_message = await message.answer(
            "❌ <b>Пароль не может быть пустым!</b>\n\n"
            "Пожалуйста, введите пароль от вашего игрового аккаунта:",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_game_login")
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)
        return
    
    logger.info(f"Пользователь @{message.from_user.username} ввел пароль")
    await state.update_data(
        game_password=game_password,
        account_data=f"Логин: {data.get('game_login')}\nПароль: {game_password}"
    )
    
    # Проверяем, находимся ли мы в режиме редактирования
    if data.get("total_cost"):
        # Возвращаемся к сводке
        await show_order_summary(message, state)
        return
    
    # Переходим к дополнительным деталям
    sent_message = await message.answer(
        "📝 <b>Дополнительные детали</b>\n\n"
        "Введите дополнительные пожелания или детали заказа (или напишите 'нет'):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_game_password")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_details)

@router.message(OrderStates.entering_details)
async def handle_details(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода дополнительных деталей"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    logger.info(f"Пользователь @{message.from_user.username} ввел дополнительные детали")
    
    details = message.text if message.text.lower() != "нет" else None
    await state.update_data(details=details)
    
    # Всегда показываем финальный заказ после ввода деталей
    await show_order_summary(message, state)

@router.callback_query(F.data.startswith("target_main_rank:"))
async def handle_target_main_rank_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора целевого основного ранга"""
    target_main_rank = call.data.split(":")[1]
    logger.info(f"Пользователь @{call.from_user.username} выбрал целевой основной ранг: {target_main_rank}")
    
    await state.update_data(target_main_rank=target_main_rank)
    
    # Если выбран Мифик, переходим к вводу звезд
    if target_main_rank == "Мифик":
        await state.update_data(target_rank="Мифик")
        await call.message.edit_text(
            "⭐ <b>Мифик ранг</b>\n\n"
            "Введите желаемое количество звезд (0-1000):",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_target_main_ranks")
        )
        await state.set_state(OrderStates.entering_target_mythic)
    else:
        # ИСПРАВЛЕНО: Добавляем current_rank как второй аргумент
        data = await state.get_data()
        current_rank = data.get("current_rank")
        
        # Показываем градации для других рангов
        await call.message.edit_text(
            f"🎯 <b>{target_main_rank}</b>\n\n"
            "Выберите точный ранг:",
            parse_mode="HTML",
            reply_markup=target_rank_gradations_keyboard(target_main_rank, current_rank)
        )
        await state.set_state(OrderStates.choosing_target_gradation)
    
    await call.answer()

async def proceed_to_next_step(obj, state: FSMContext):
    """Переход к следующему этапе создания заказа"""
    data = await state.get_data()
    boost_type = data.get("boost_type")
    
    # Определяем следующий шаг в зависимости от типа буста
    if boost_type == "account":
        # Для буста через аккаунт сначала запрашиваем логин
        if isinstance(obj, CallbackQuery):
            await obj.message.edit_text(
                "👤 <b>Логин аккаунта</b>\n\n"
                "Введите логин от вашего игрового аккаунта:",
                parse_mode="HTML",
                reply_markup=back_keyboard("back_to_target_gradation")  
            )
        else:
            sent_message = await obj.answer(
                "👤 <b>Логин аккаунта</b>\n\n"
                "Введите логин от вашего игрового аккаунта:",
                parse_mode="HTML",
                reply_markup=back_keyboard("back_to_target_gradation")
            )
            await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state(OrderStates.entering_game_login)
    else:
        # Для остальных типов буста запрашиваем игровой ID
        if isinstance(obj, CallbackQuery):
            await obj.message.edit_text(
                "🆔 <b>Игровой ID</b>\n\n"
                "Введите ваш игровой ID:",
                parse_mode="HTML",
                reply_markup=back_keyboard("back_to_target_gradation")
            )
        else:
            sent_message = await obj.answer(
                "🆔 <b>Игровой ID</b>\n\n"
                "Введите ваш игровой ID:",
                parse_mode="HTML",
                reply_markup=back_keyboard("back_to_target_gradation")
            )
            await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state(OrderStates.entering_game_id)
        
@router.callback_query(F.data == "edit_order")
async def edit_order(call: CallbackQuery, state: FSMContext):
    """Редактирование заказа"""
    logger.info(f"Пользователь @{call.from_user.username} хочет редактировать заказ")
    
    data = await state.get_data()
    
    await call.message.edit_text(
        "✏️ <b>Редактирование заказа</b>\n\n"
        "Выберите поле для изменения:",
        parse_mode="HTML",
        reply_markup=edit_order_keyboard(data)
    )
    await call.answer()

@router.callback_query(F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    """Отмена заказа"""
    logger.info(f"Пользователь @{call.from_user.username} отменил заказ")
    
    await call.message.edit_text(
        "❌ <b>Заказ отменен</b>\n\n"
        "Можете начать создание заказа заново через главное меню.",
        parse_mode="HTML"
    )
    
    await state.clear()
    await call.answer("Заказ отменен")

@router.callback_query(F.data == "back_to_summary")
async def back_to_summary(call: CallbackQuery, state: FSMContext):
    """Возврат к сводке заказа"""
    logger.info(f"Пользователь @{call.from_user.username} вернулся к сводке заказа")
    
    data = await state.get_data()
    
    # Пересчитываем стоимость на случай изменений
    base_cost = await calculate_order_cost(data)
    total_cost, currency = await calculate_total_order_cost(base_cost, data.get("boost_type"), data.get("region"))
    
    await state.update_data(base_cost=base_cost, total_cost=total_cost, currency=currency)
    
    # Формируем текст заказа
    summary_text = await format_order_summary(data, total_cost, currency)
    
    await call.message.edit_text(
        summary_text,
        parse_mode="HTML",
        reply_markup=confirm_order_keyboard()
    )
    await state.set_state(OrderStates.confirming_order)
    await call.answer()

@router.callback_query(F.data == "edit_service_type")
async def edit_service_type(call: CallbackQuery, state: FSMContext):
    """Редактирование типа услуги"""
    await call.message.edit_text(
        "🛒 <b>Каталог услуг</b>\n\n"
        "Выберите тип услуги:",
        parse_mode="HTML",
        reply_markup=service_catalog_keyboard()
    )
    await state.set_state(OrderStates.choosing_service)
    await call.answer()

@router.callback_query(F.data == "edit_boost_type")
async def edit_boost_type(call: CallbackQuery, state: FSMContext):
    """Редактирование типа буста"""
    data = await state.get_data()
    service_type = data.get("service_type")
    
    if service_type == "regular_boost":
        await call.message.edit_text(
            "🎮 <b>Обычный буст</b>\n\n"
            "Выберите тип буста:",
            parse_mode="HTML",
            reply_markup=regular_boost_type_keyboard()
        )
    elif service_type == "hero_boost":
        await call.message.edit_text(
            "🎯 <b>Буст на конкретного персонажа</b>\n\n"
            "Выберите тип буста:",
            parse_mode="HTML",
            reply_markup=hero_boost_type_keyboard()
        )
    
    await state.set_state(OrderStates.choosing_boost_type)
    await call.answer()

@router.callback_query(F.data == "edit_current_rank")
async def edit_current_rank(call: CallbackQuery, state: FSMContext):
    """Редактирование текущего ранга"""
    await call.message.edit_text(
        "📊 <b>Выбор текущего ранга</b>\n\n"
        "Выберите ваш текущий ранг:",
        parse_mode="HTML",
        reply_markup=main_ranks_keyboard()
    )
    await state.set_state(OrderStates.choosing_main_rank)
    await call.answer()

@router.callback_query(F.data == "edit_target_rank")
async def edit_target_rank(call: CallbackQuery, state: FSMContext):
    """Редактирование целевого ранга"""
    data = await state.get_data()
    current_rank = data.get("current_rank")
    
    await call.message.edit_text(
        "🎯 <b>Выбор желаемого ранга</b>\n\n"
        "Выберите желаемый ранг:",
        parse_mode="HTML",
        reply_markup=target_main_ranks_keyboard(current_rank)
    )
    await state.set_state(OrderStates.choosing_target_main_rank)
    await call.answer()

@router.callback_query(F.data == "edit_lane")
async def edit_lane(call: CallbackQuery, state: FSMContext):
    """Редактирование лайна"""
    await call.message.edit_text(
        "🎮 <b>Выбор лайна</b>\n\n"
        "Выберите ваш предпочитаемый лайн:",
        parse_mode="HTML",
        reply_markup=lanes_keyboard()
    )
    await state.set_state(OrderStates.choosing_lane)
    await call.answer()

@router.callback_query(F.data == "edit_heroes")
@router.callback_query(F.data == "edit_time")
async def edit_time(call: CallbackQuery, state: FSMContext):
    """Редактирование времени"""
    await call.message.edit_text(
        "⏰ <b>Удобное время</b>\n\n"
        "Введите удобное время для совместной игры:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_summary")
    )
    await state.set_state(OrderStates.entering_preferred_time)
    await call.answer()

@router.callback_query(F.data == "edit_contacts")
async def edit_contacts(call: CallbackQuery, state: FSMContext):
    """Редактирование контактов"""
    await call.message.edit_text(
        "📞 <b>Контакты</b>\n\n"
        "Введите ваши контакты для связи (Discord, Telegram и т.д.):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_summary")
    )
    await state.set_state(OrderStates.entering_contact_info)
    await call.answer()

@router.callback_query(F.data == "edit_details")
@router.callback_query(F.data == "edit_account")
async def edit_account(call: CallbackQuery, state: FSMContext):
    """Редактирование данных аккаунта"""
    await call.message.edit_text(
        "🔐 <b>Данные аккаунта</b>\n\n"
        "Введите данные аккаунта в формате:\n"
        "<code>Логин: ваш_логин\n"
        "Пароль: ваш_пароль</code>",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_summary")
    )
    await state.set_state(OrderStates.entering_account_data)
    await call.answer()

# === НОВЫЕ ОБРАБОТЧИКИ ДЛЯ РЕДАКТИРОВАНИЯ ОТДЕЛЬНЫХ ПОЛЕЙ ===

@router.callback_query(F.data == "edit_login")
async def edit_login(call: CallbackQuery, state: FSMContext):
    """Редактирование логина"""
    await call.message.edit_text(
        "👤 <b>Логин аккаунта</b>\n\n"
        "Введите новый логин от вашего игрового аккаунта:",
        parse_mode="HTML",
        reply_markup=back_keyboard("edit_order")
    )
    await state.set_state(OrderStates.entering_game_login)
    await call.answer()

@router.callback_query(F.data == "edit_password")
async def edit_password(call: CallbackQuery, state: FSMContext):
    """Редактирование пароля"""
    await call.message.edit_text(
        "🔐 <b>Пароль аккаунта</b>\n\n"
        "Введите новый пароль от вашего игрового аккаунта:",
        parse_mode="HTML",
        reply_markup=back_keyboard("edit_order")
    )
    await state.set_state(OrderStates.entering_game_password)
    await call.answer()

@router.callback_query(F.data == "edit_game_id")
async def edit_game_id(call: CallbackQuery, state: FSMContext):
    """Редактирование игрового ID"""
    await call.message.edit_text(
        "🆔 <b>Игровой ID</b>\n\n"
        "Введите новый игровой ID:",
        parse_mode="HTML",
        reply_markup=back_keyboard("edit_order")
    )
    await state.set_state(OrderStates.entering_game_id)
    await call.answer()

@router.callback_query(F.data == "edit_lane")
async def edit_lane(call: CallbackQuery, state: FSMContext):
    """Редактирование лайна"""
    await call.message.edit_text(
        "🎮 <b>Выбор лайна</b>\n\n"
        "Выберите новый предпочитаемый лайн:",
        parse_mode="HTML",
        reply_markup=lanes_keyboard()
    )
    await state.set_state(OrderStates.choosing_lane)
    await call.answer()

@router.callback_query(F.data == "edit_heroes")
async def edit_heroes(call: CallbackQuery, state: FSMContext):
    """Редактирование мейнов"""
    await call.message.edit_text(
        "🎭 <b>Мейны</b>\n\n"
        "Напишите ваших новых основных героев (мейнов):",
        parse_mode="HTML",
        reply_markup=back_keyboard("edit_order")
    )
    await state.set_state(OrderStates.entering_heroes)
    await call.answer()

@router.callback_query(F.data == "edit_time")
async def edit_time(call: CallbackQuery, state: FSMContext):
    """Редактирование времени"""
    await call.message.edit_text(
        "⏰ <b>Удобное время</b>\n\n"
        "Укажите новое удобное время для игры:",
        parse_mode="HTML",
        reply_markup=back_keyboard("edit_order")
    )
    await state.set_state(OrderStates.entering_preferred_time)
    await call.answer()

@router.callback_query(F.data == "edit_contact")
async def edit_contact(call: CallbackQuery, state: FSMContext):
    """Редактирование контактов"""
    await call.message.edit_text(
        "📞 <b>Контактная информация</b>\n\n"
        "Введите новые контактные данные:",
        parse_mode="HTML",
        reply_markup=back_keyboard("edit_order")
    )
    await state.set_state(OrderStates.entering_contact_info)
    await call.answer()

@router.callback_query(F.data == "edit_details")
async def edit_details(call: CallbackQuery, state: FSMContext):
    """Редактирование деталей"""
    await call.message.edit_text(
        "📝 <b>Дополнительные детали</b>\n\n"
        "Введите новые дополнительные пожелания или детали заказа:",
        parse_mode="HTML",
        reply_markup=back_keyboard("edit_order")
    )
    await state.set_state(OrderStates.entering_details)
    await call.answer()
    
async def show_order_confirmation(call, state: FSMContext):
    """Показ подтверждения заказа"""
    data = await state.get_data()
    total_cost = data.get("total_cost", 0)
    currency = data.get("currency", "сом")
    
    # Формируем текст заказа
    summary_text = await format_order_summary(data, total_cost, currency)
    
    await call.message.edit_text(
        summary_text,
        parse_mode="HTML",
        reply_markup=confirm_order_keyboard()
    )
    
    await state.set_state(OrderStates.confirming_order)


@router.callback_query(F.data.startswith("confirm_payment:"))
async def confirm_payment(call: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка подтвержденной оплаты и создание заказа"""
    payment_method = call.data.split(":")[1]
    logger.info(f"Пользователь @{call.from_user.username} подтвердил оплату методом {payment_method}")
    
    data = await state.get_data()
    user_id = data.get("user_id")
    final_cost = data.get("final_cost", 0)
    region = data.get("region")
    currency = data.get("currency", "сом")
    discount_percent = data.get("discount_percent", 0)
    
    # Проверяем наличие необходимых данных
    if not user_id or final_cost <= 0:
        await call.answer("Ошибка: недостаточно данных", show_alert=True)
        return
    
    # Получаем пользователя
    user = await get_user_by_id(user_id)
    if not user:
        await call.answer("Пользователь не найден", show_alert=True)
        return
    
    try:
        # Обрабатываем скидку если есть
        if discount_percent > 0:
            await apply_user_discount(user_id)
        
        # Обрабатываем оплату в зависимости от метода
        if payment_method == "balance":
            # Полная оплата с баланса
            balance_field = get_balance_field_from_region(region)
            await update_user_balance_by_region(user_id, balance_field, -final_cost)
            payment_desc = f"Оплачено с баланса: {final_cost:.0f} {currency}"
            
        elif payment_method == "bonus":
            # Полная оплата бонусами
            success, message = await use_user_bonus(user_id, final_cost, currency)
            if not success:
                await call.answer(f"Ошибка оплаты: {message}", show_alert=True)
                return
            payment_desc = f"Оплачено бонусами: {final_cost:.0f} {currency}"
            
        elif payment_method == "mixed":
            # Смешанная оплата
            bonus_amount = data.get("bonus_amount", 0)
            balance_amount = data.get("balance_amount", 0)
            
            # Списываем бонусы
            success, message = await use_user_bonus(user_id, bonus_amount, currency)
            if not success:
                await call.answer(f"Ошибка списания бонусов: {message}", show_alert=True)
                return
            
            # Списываем с баланса
            balance_field = get_balance_field_from_region(region)
            await update_user_balance_by_region(user_id, balance_field, -balance_amount)
            payment_desc = f"Оплачено: {bonus_amount:.0f} {currency} бонусами + {balance_amount:.0f} {currency} с баланса"
            
        elif payment_method == "partial_bonus":
            # Частичная оплата бонусами
            bonus_amount = data.get("bonus_amount", 0)
            balance_amount = data.get("balance_amount", 0)
            
            if bonus_amount > 0:
                success, message = await use_user_bonus(user_id, bonus_amount, currency)
                if not success:
                    await call.answer(f"Ошибка списания бонусов: {message}", show_alert=True)
                    return
            
            if balance_amount > 0:
                balance_field = get_balance_field_from_region(region)
                await update_user_balance_by_region(user_id, balance_field, -balance_amount)
            
            if bonus_amount > 0 and balance_amount > 0:
                payment_desc = f"Оплачено: {bonus_amount:.0f} {currency} бонусами + {balance_amount:.0f} {currency} с баланса"
            elif bonus_amount > 0:
                payment_desc = f"Оплачено бонусами: {bonus_amount:.0f} {currency}"
            else:
                payment_desc = f"Оплачено с баланса: {balance_amount:.0f} {currency}"
        
        # Подготавливаем данные для создания заказа
        order_data = {
            "order_id": str(uuid.uuid4())[:8].upper(),
            "user_id": user_id,
            "service_type": data.get("service_type"),
            "boost_type": data.get("boost_type"),
            "current_rank": data.get("current_rank"),
            "target_rank": data.get("target_rank"),
            "current_mythic_stars": data.get("current_mythic_stars"),
            "target_mythic_stars": data.get("target_mythic_stars"),
            "coaching_hours": data.get("coaching_hours"),
            "coaching_topic": data.get("coaching_topic"),
            "lane": data.get("lane"),
            "heroes_mains": data.get("heroes_mains"),
            "game_id": data.get("game_id"),
            "game_login": data.get("game_login"),
            "game_password": data.get("game_password"),
            "preferred_time": data.get("preferred_time"),
            "contact_info": data.get("contact_info"),
            "account_data": data.get("account_data"),
            "details": data.get("details"),
            "total_cost": final_cost,
            "currency": currency,
            "status": "pending"
        }
        
        # Сохраняем заказ в базу
        order = await create_order(order_data)
        
        if not order:
            raise Exception("Не удалось создать заказ в базе данных")
        
        # Отправляем уведомление админу
        await send_admin_notification(bot, order, user)
        
        # Формируем сообщение об успехе
        success_text = f"✅ <b>Заказ создан!</b>\n\n"
        success_text += f"🆔 <b>Номер заказа:</b> <code>{order.order_id}</code>\n"
        success_text += f"💰 <b>Стоимость:</b> {final_cost:.0f} {currency}\n"
        
        if discount_percent > 0:
            original_cost = data.get("original_cost", final_cost)
            success_text += f"🎁 <b>Применена скидка:</b> {discount_percent}% (-{original_cost - final_cost:.0f} {currency})\n"
        
        success_text += f"💳 <b>Оплата:</b> {payment_desc}\n"
        success_text += f"📊 <b>Статус:</b> Ожидает подтверждения\n\n"
        success_text += f"Ваш заказ отправлен на рассмотрение.\n"
        success_text += f"Ожидайте подтверждения от админа в ближайшее время\n\n"
        success_text += f"📦 Посмотреть заказ можно в разделе «Мои заказы»"
        
        await call.message.edit_text(
            success_text,
            parse_mode="HTML"
        )
        
        logger.info(f"Заказ {order.order_id} создан пользователем @{call.from_user.username} с оплатой {payment_method}")
        
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}")
        
        # Пытаемся вернуть средства при ошибке
        try:
            if payment_method == "balance":
                balance_field = get_balance_field_from_region(region)
                await update_user_balance_by_region(user_id, balance_field, final_cost)
            elif payment_method in ["bonus", "mixed", "partial_bonus"]:
                # Для бонусов возврат сложнее, но можно добавить логику восстановления
                pass
        except Exception as refund_error:
            logger.error(f"Ошибка возврата средств: {refund_error}")
        
        await call.message.edit_text(
            "❌ <b>Ошибка создания заказа</b>\n\n"
            "Попробуйте позже или обратитесь к администратору.\n"
            "При ошибке оплаты средства будут возвращены.",
            parse_mode="HTML"
        )
    
    await state.clear()
    await call.answer("Заказ создан!")
@router.callback_query(F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    """Переадресация на новую систему оплаты"""
    logger.info(f"Пользователь @{call.from_user.username} пытается подтвердить заказ")
    await call.answer("Теперь нужно выбрать способ оплаты!", show_alert=True)
    
    # Переадресуем на выбор способа оплаты
    from app.handlers.user.payment import choose_payment_method
    await choose_payment_method(call, state)

async def send_admin_notification(bot: Bot, order, user):
    """Отправка уведомления админу о новом заказе"""
    
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
    
    text = f"🚨 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
    text += f"🆔 <b>ID заказа:</b> <code>{order.order_id}</code>\n"
    if user.username:
        text += f"👤 <b>Пользователь:</b> @{user.username} ({user.tg_id})\n"
    else:
        text += f"👤 <b>Пользователь:</b> <a href='tg://user?id={user.tg_id}'>Связаться</a> ({user.tg_id})\n"
    text += f"🌍 <b>Регион:</b> {user.region}\n\n"
    
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
            text += f"🎯 <b>Желаемый:</b> Мифик {order.target_mythic_stars or 0} ⭐\n"
        else:
            text += f"🎯 <b>Желаемый:</b> {order.target_rank}\n"
        
        if order.lane:
            text += f"🎮 <b>Лайн:</b> {order.lane}\n"
        if order.heroes_mains:
            text += f"🎭 <b>Мейны:</b> {order.heroes_mains}\n"
        if order.game_id:
            text += f"🆔 <b>ID игры:</b> {order.game_id}\n"
        if order.preferred_time:
            text += f"⏰ <b>Время:</b> {order.preferred_time}\n"
    
    if order.contact_info:
        text += f"📞 <b>Контакты:</b> {order.contact_info}\n"
    if order.details:
        text += f"📝 <b>Детали:</b> {order.details}\n"
    
    text += f"\n💰 <b>Стоимость:</b> {order.total_cost:.0f} сом"
    
    # Создаем клавиатуру для админа
    from app.keyboards.admin.order_management import admin_order_notification_keyboard
    admin_keyboard = admin_order_notification_keyboard(order.order_id)
    
    # Отправляем всем админам из базы данных
    sent_count = 0
    for admin in admins:
        try:
            await bot.send_message(
                chat_id=admin.tg_id,
                text=text,
                parse_mode="HTML",
                reply_markup=admin_keyboard
            )
            logger.info(f"Уведомление о заказе {order.order_id} отправлено админу @{admin.username} ({admin.tg_id})")
            sent_count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу @{admin.username} ({admin.tg_id}): {e}")
    
    logger.info(f"Уведомление о заказе {order.order_id} отправлено {sent_count} из {len(admins)} админов")

# Добавляем обработчики кнопок "Назад"
@router.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(call: CallbackQuery, state: FSMContext):
    """Возврат к каталогу услуг"""
    await call.message.edit_text(
        "🛒 <b>Каталог услуг</b>\n\n"
        "Выберите тип услуги:",
        parse_mode="HTML",
        reply_markup=service_catalog_keyboard()
    )
    await state.set_state(OrderStates.choosing_service)
    await call.answer()
    
@router.callback_query(F.data == "back_to_boost_type")
async def back_to_boost_type(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору типа буста"""
    data = await state.get_data()
    service_type = data.get("service_type")
    
    if service_type == "regular_boost":
        await call.message.edit_text(
            "🎮 <b>Обычный буст</b>\n\n"
            "Выберите тип буста:",
            parse_mode="HTML",
            reply_markup=regular_boost_type_keyboard()
        )
    elif service_type == "hero_boost":
        await call.message.edit_text(
            "🎯 <b>Буст на конкретного персонажа</b>\n\n"
            "Выберите тип буста:",
            parse_mode="HTML",
            reply_markup=hero_boost_type_keyboard()
        )
    
    await state.set_state(OrderStates.choosing_boost_type)
    await call.answer()

@router.callback_query(F.data == "back_to_main_ranks")
async def back_to_main_ranks(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору основного ранга"""
    await call.message.edit_text(
        "📊 <b>Выбор текущего ранга</b>\n\n"
        "Выберите ваш текущий ранг:",
        parse_mode="HTML",
        reply_markup=main_ranks_keyboard()
    )
    await state.set_state(OrderStates.choosing_main_rank)
    await call.answer()

@router.callback_query(F.data == "back_to_target_main_ranks")
async def back_to_target_main_ranks(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору целевого основного ранга"""
    data = await state.get_data()
    current_rank = data.get("current_rank")
    
    await call.message.edit_text(
        "🎯 <b>Выбор желаемого ранга</b>\n\n"
        "Выберите желаемый ранг:",
        parse_mode="HTML",
        reply_markup=target_main_ranks_keyboard(current_rank)
    )
    await state.set_state(OrderStates.choosing_target_main_rank)
    await call.answer()

@router.callback_query(F.data == "back_to_target_gradation")
async def back_to_target_gradation(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору градации целевого ранга"""
    data = await state.get_data()
    target_main_rank = data.get("target_main_rank")
    current_rank = data.get("current_rank")  # Добавляем current_rank
    
    await call.message.edit_text(
        f"🎯 <b>{target_main_rank}</b>\n\n"
        "Выберите точный ранг:",
        parse_mode="HTML",
        reply_markup=target_rank_gradations_keyboard(target_main_rank, current_rank)  # Передаем оба аргумента
    )
    await state.set_state(OrderStates.choosing_target_gradation)
    await call.answer()

@router.callback_query(F.data == "back_to_game_id")
async def back_to_game_id(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу игрового ID"""
    await call.message.edit_text(
        "🆔 <b>Игровой ID</b>\n\n"
        "Введите ваш игровой ID:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_target_gradation")
    )
    await state.set_state(OrderStates.entering_game_id)
    await call.answer()

@router.callback_query(F.data == "back_to_heroes")
async def back_to_heroes(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу мейнов"""
    await call.message.edit_text(
        "🎯 <b>Мейны</b>\n\n"
        "Напишите ваших основных героев (мейнов):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_game_id")
    )
    await state.set_state(OrderStates.entering_heroes)
    await call.answer()

@router.callback_query(F.data == "back_to_preferred_time")
async def back_to_preferred_time(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу времени"""
    await call.message.edit_text(
        "⏰ <b>Удобное время</b>\n\n"
        "Введите удобное время для совместной игры:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_heroes")
    )
    await state.set_state(OrderStates.entering_preferred_time)
    await call.answer()

@router.callback_query(F.data == "back_to_contact_info")
async def back_to_contact_info(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу контактов"""
    await call.message.edit_text(
        "📞 <b>Контакты</b>\n\n"
        "Введите ваши контакты для связи (Discord, Telegram и т.д.):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_coaching_topic")
    )
    await state.set_state(OrderStates.entering_contact_info)
    await call.answer()

@router.callback_query(F.data == "back_to_coaching_topic")
async def back_to_coaching_topic(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу темы обучения"""
    await call.message.edit_text(
        "📚 <b>Тема обучения</b>\n\n"
        "Что именно хотите изучить? (герой, роль, сборка, тактика и т.д.):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_catalog")
    )
    await state.set_state(OrderStates.entering_coaching_topic)
    await call.answer()

@router.callback_query(F.data == "back_to_account_data")
async def back_to_account_data(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу данных аккаунта"""
    await call.message.edit_text(
        "🔐 <b>Данные аккаунта</b>\n\n"
        "Введите данные аккаунта в формате:\n"
        "<code>Логин: ваш_логин\n"
        "Пароль: ваш_пароль</code>",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_target_gradation")
    )
    await state.set_state(OrderStates.entering_account_data)
    await call.answer()

# === НОВЫЕ ОБРАБОТЧИКИ КНОПОК "НАЗАД" ===

@router.callback_query(F.data == "back_to_game_login")
async def back_to_game_login(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу логина"""
    await call.message.edit_text(
        "👤 <b>Логин аккаунта</b>\n\n"
        "Введите логин от вашего игрового аккаунта:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_target_gradation")
    )
    await state.set_state(OrderStates.entering_game_login)
    await call.answer()

@router.callback_query(F.data == "back_to_game_password")
async def back_to_game_password(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу пароля"""
    await call.message.edit_text(
        "🔐 <b>Пароль аккаунта</b>\n\n"
        "Введите пароль от вашего игрового аккаунта:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_game_login")
    )
    await state.set_state(OrderStates.entering_game_password)
    await call.answer()