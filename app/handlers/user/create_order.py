from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from app.states.user_states import OrderStates
from app.keyboards.user.order_keyboards import (
    service_catalog_keyboard, regular_boost_type_keyboard, hero_boost_type_keyboard,
    main_ranks_keyboard, rank_gradations_keyboard, target_main_ranks_keyboard, 
    target_rank_gradations_keyboard, lanes_keyboard, confirm_order_keyboard, cancel_keyboard,
    back_keyboard
)
from app.config import MAIN_RANKS, RANK_GRADATIONS, RANKS, COACHING_PRICES
from app.database.crud import get_user_by_tg_id, create_order
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

async def delete_previous_messages(state: FSMContext):
    """Удаление предыдущих сообщений"""
    data = await state.get_data()
    
    # Удаляем сообщение бота
    if data.get("last_bot_message_id"):
        try:
            # Здесь нужно получить bot instance, но для простоты пропустим
            pass
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение бота: {e}")
    
    # Удаляем сообщение пользователя
    if data.get("last_user_message"):
        try:
            await data["last_user_message"].delete()
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение пользователя: {e}")

@router.message(F.text == "🎮 Создать заказ")
async def start_order_creation(message: Message, state: FSMContext):
    """Начало создания заказа"""
    logger.info(f"Пользователь @{message.from_user.username} начал создание заказа")
    
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Напишите /start для регистрации.")
        return
    
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
    
    # Теперь просим выбрать основной ранг
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

@router.callback_query(F.data.startswith("target_main_rank:"))
async def handle_target_main_rank_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора основного целевого ранга"""
    main_rank = call.data.split(":")[1]
    logger.info(f"Пользователь @{call.from_user.username} выбрал целевой основной ранг: {main_rank}")
    
    await state.update_data(target_main_rank=main_rank)
    
    # Если выбран Мифик, сразу переходим к вводу звезд
    if main_rank == "Мифик":
        await state.update_data(target_rank="Мифик")
        await call.message.edit_text(
            "⭐ <b>Мифик ранг</b>\n\n"
            "Введите количество желаемых звезд (0-1000):",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_target_main_ranks")
        )
        await state.set_state(OrderStates.entering_target_mythic)
    else:
        # Получаем текущий ранг для валидации
        data = await state.get_data()
        current_rank = data.get("current_rank")
        
        # Показываем градации для целевого ранга
        await call.message.edit_text(
            f"🎯 <b>{main_rank}</b>\n\n"
            "Выберите точный желаемый ранг:",
            parse_mode="HTML",
            reply_markup=target_rank_gradations_keyboard(main_rank, current_rank)
        )
        await state.set_state(OrderStates.choosing_target_gradation)
    
    await call.answer()

@router.callback_query(F.data.startswith("rank:"))
async def handle_rank_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора конкретного ранга"""
    rank = call.data.split(":")[1]
    current_state = await state.get_state()
    
    if current_state == OrderStates.choosing_rank_gradation:
        logger.info(f"Пользователь @{call.from_user.username} выбрал текущий ранг: {rank}")
        
        await state.update_data(current_rank=rank)
        
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
        
        # Переходим к следующему этапу
        await proceed_to_next_step(call, state)
    
    await call.answer()

# Обработчики навигации
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
    """Возврат к выбору основных рангов"""
    await call.message.edit_text(
        "📊 <b>Выбор текущего ранга</b>\n\n"
        "Выберите ваш текущий ранг:",
        parse_mode="HTML",
        reply_markup=main_ranks_keyboard()
    )
    await state.set_state(OrderStates.choosing_main_rank)
    await call.answer()

@router.callback_query(F.data == "back_to_current_rank")
async def back_to_current_rank(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору текущего ранга"""
    data = await state.get_data()
    main_rank = data.get("current_main_rank")
    
    if main_rank == "Мифик":
        await call.message.edit_text(
            "⭐ <b>Мифик ранг</b>\n\n"
            "Введите количество ваших текущих звезд (0-1000):",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_main_ranks")
        )
        await state.set_state(OrderStates.entering_current_mythic)
    else:
        await call.message.edit_text(
            f"📊 <b>{main_rank}</b>\n\n"
            "Выберите точный ранг:",
            parse_mode="HTML",
            reply_markup=rank_gradations_keyboard(main_rank)
        )
        await state.set_state(OrderStates.choosing_rank_gradation)
    
    await call.answer()

@router.callback_query(F.data == "back_to_target_main_ranks")
async def back_to_target_main_ranks(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору основных целевых рангов"""
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

@router.callback_query(F.data == "back_to_target_rank")
async def back_to_target_rank(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору целевого ранга"""
    data = await state.get_data()
    target_main_rank = data.get("target_main_rank")
    current_rank = data.get("current_rank")
    
    if target_main_rank == "Мифик":
        await call.message.edit_text(
            "⭐ <b>Мифик ранг</b>\n\n"
            "Введите количество желаемых звезд (0-1000):",
            parse_mode="HTML",
            reply_markup=back_keyboard("back_to_target_main_ranks")
        )
        await state.set_state(OrderStates.entering_target_mythic)
    else:
        await call.message.edit_text(
            f"🎯 <b>{target_main_rank}</b>\n\n"
            "Выберите точный желаемый ранг:",
            parse_mode="HTML",
            reply_markup=target_rank_gradations_keyboard(target_main_rank, current_rank)
        )
        await state.set_state(OrderStates.choosing_target_gradation)
    
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
        reply_markup=back_keyboard("back_to_target_rank")
    )
    await state.set_state(OrderStates.entering_account_data)
    await call.answer()

@router.callback_query(F.data == "back_to_game_id")
async def back_to_game_id(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу игрового ID"""
    await call.message.edit_text(
        "🎮 <b>Игровой ID</b>\n\n"
        "Введите ваш игровой ID или никнейм:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_target_rank")
    )
    await state.set_state(OrderStates.entering_game_id)
    await call.answer()

@router.callback_query(F.data == "back_to_lane")
async def back_to_lane(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору лайна"""
    await call.message.edit_text(
        "🎮 <b>Выбор лайна</b>\n\n"
        "Выберите ваш предпочитаемый лайн:",
        parse_mode="HTML",
        reply_markup=lanes_keyboard()
    )
    await state.set_state(OrderStates.choosing_lane)
    await call.answer()

@router.callback_query(F.data == "back_to_heroes")
async def back_to_heroes(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу мейнов"""
    await call.message.edit_text(
        "🎯 <b>Мейны</b>\n\n"
        "Напишите ваших основных героев (мейнов):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_lane")
    )
    await state.set_state(OrderStates.entering_heroes)
    await call.answer()

@router.callback_query(F.data == "back_to_preferred_time")
async def back_to_preferred_time(call: CallbackQuery, state: FSMContext):
    """Возврат к вводу удобного времени"""
    await call.message.edit_text(
        "⏰ <b>Удобное время</b>\n\n"
        "Введите удобное время для совместной игры:",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_heroes")
    )
    await state.set_state(OrderStates.entering_preferred_time)
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

# Обработчики ввода текста с автоудалением
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
    
    sent_message = await message.answer(
        "📞 <b>Контакты</b>\n\n"
        "Введите ваши контакты для связи (Discord, Telegram и т.д.):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_coaching_topic")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_contact_info)

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
    
    sent_message = await message.answer(
        "📝 <b>Дополнительные детали</b>\n\n"
        "Введите дополнительные пожелания или детали заказа (или напишите 'нет'):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_contact_info")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_details)

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
        
        # Переходим к выбору целевого основного ранга
        data = await state.get_data()
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
        data = await state.get_data()
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
        
        # Переходим к следующему этапу
        await proceed_to_next_step(message, state)
        
    except ValueError:
        sent_message = await message.answer(
            "❌ Введите корректное число.",
            reply_markup=back_keyboard("back_to_target_main_ranks")
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)

@router.message(OrderStates.entering_account_data)
async def handle_account_data(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода данных аккаунта"""
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Удаляем предыдущее сообщение бота
    data = await state.get_data()
    if data.get("last_bot_message_id"):
        await delete_bot_message_safe(bot, message.chat.id, data["last_bot_message_id"])
    
    logger.info(f"Пользователь @{message.from_user.username} ввел данные аккаунта")
    
    await state.update_data(account_data=message.text)
    
    sent_message = await message.answer(
        "📝 <b>Дополнительные детали</b>\n\n"
        "Введите дополнительные пожелания или детали заказа (или напишите 'нет'):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_account_data")
    )
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(OrderStates.entering_details)

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
    
    sent_message = await message.answer(
        "📝 <b>Дополнительные детали</b>\n\n"
        "Введите дополнительные пожелания или детали заказа (или напишите 'нет'):",
        parse_mode="HTML",
        reply_markup=back_keyboard("back_to_preferred_time")
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
    
    # Рассчитываем стоимость и показываем финальный заказ
    await show_order_summary(message, state)

# Также обновляем proceed_to_next_step
async def proceed_to_next_step(message_or_call, state: FSMContext):
    """Переход к следующему этапу после выбора рангов"""
    data = await state.get_data()
    boost_type = data.get("boost_type")
    
    if boost_type in ["account", "mmr", "winrate"]:
        # Нужны данные аккаунта
        text = (
            "🔐 <b>Данные аккаунта</b>\n\n"
            "Введите данные аккаунта в формате:\n"
            "<code>Логин: ваш_логин\n"
            "Пароль: ваш_пароль</code>"
        )
        keyboard = back_keyboard("back_to_target_rank")
        
        if hasattr(message_or_call, 'message'):
            await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            # Удаляем предыдущее сообщение бота перед отправкой нового
            if data.get("last_bot_message_id"):
                try:
                    await message_or_call.bot.delete_message(
                        chat_id=message_or_call.chat.id, 
                        message_id=data["last_bot_message_id"]
                    )
                except:
                    pass
                    
            sent_message = await message_or_call.answer(text, parse_mode="HTML", reply_markup=keyboard)
            await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state(OrderStates.entering_account_data)
        
    elif boost_type == "shared":
        # Нужен игровой ID
        text = (
            "🎮 <b>Игровой ID</b>\n\n"
            "Введите ваш игровой ID или никнейм:"
        )
        keyboard = back_keyboard("back_to_target_rank")
        
        if hasattr(message_or_call, 'message'):
            await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            # Удаляем предыдущее сообщение бота перед отправкой нового
            if data.get("last_bot_message_id"):
                try:
                    await message_or_call.bot.delete_message(
                        chat_id=message_or_call.chat.id, 
                        message_id=data["last_bot_message_id"]
                    )
                except:
                    pass
                    
            sent_message = await message_or_call.answer(text, parse_mode="HTML", reply_markup=keyboard)
            await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state(OrderStates.entering_game_id)

async def show_order_summary(message: Message, state: FSMContext):
    """Показ итогового заказа для подтверждения"""
    data = await state.get_data()
    
    # Рассчитываем стоимость
    base_cost = await calculate_order_cost(data)
    total_cost, currency = calculate_total_order_cost(base_cost, data.get("boost_type"), data.get("region"))
    
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

async def calculate_order_cost(data):
    """Рассчитывает стоимость заказа"""
    service_type = data.get("service_type")
    region = data.get("region")
    
    if service_type == "coaching":
        # Для обучения считаем по часам
        hours = data.get("coaching_hours", 1)
        return hours * COACHING_PRICES[region]
    
    elif service_type in ["regular_boost", "hero_boost"]:
        current_rank = data.get("current_rank")
        target_rank = data.get("target_rank")
        
        # Если оба ранга Мифик, считаем по звездам
        if current_rank == "Мифик" and target_rank == "Мифик":
            current_stars = data.get("current_mythic_stars", 0)
            target_stars = data.get("target_mythic_stars", 0)
            return calculate_mythic_cost(current_stars, target_stars, region)
        
        # Если целевой ранг Мифик, а текущий нет
        elif target_rank == "Мифик" and current_rank != "Мифик":
            # Считаем до Мифик + звезды
            rank_cost = calculate_regular_rank_cost(current_rank, "Мифик", region)
            target_stars = data.get("target_mythic_stars", 0)
            mythic_cost = calculate_mythic_cost(0, target_stars, region)
            return rank_cost + mythic_cost
        
        # Обычный буст рангов
        else:
            return calculate_regular_rank_cost(current_rank, target_rank, region)
    
    return 0

async def format_order_summary(data, total_cost, currency):
    """Форматирует итоговый заказ"""
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
    
    text = f"📋 <b>Ваш заказ</b>\n\n"
    text += f"🎮 <b>Услуга:</b> {service_names.get(data.get('service_type'))}\n"
    
    if data.get("boost_type"):
        text += f"🔧 <b>Тип:</b> {boost_names.get(data.get('boost_type'))}\n"
    
    if data.get("current_rank"):
        text += f"📊 <b>Текущий ранг:</b> {data.get('current_rank')}"
        if data.get("current_mythic_stars") is not None:
            text += f" ({data.get('current_mythic_stars')} ⭐)"
        text += "\n"
    
    if data.get("target_rank"):
        text += f"🎯 <b>Желаемый ранг:</b> {data.get('target_rank')}"
        if data.get("target_mythic_stars") is not None:
            text += f" ({data.get('target_mythic_stars')} ⭐)"
        text += "\n"
    
    if data.get("lane"):
        text += f"🎮 <b>Лайн:</b> {data.get('lane')}\n"
    
    if data.get("heroes_mains"):
        text += f"🎯 <b>Мейны:</b> {data.get('heroes_mains')}\n"
    
    if data.get("preferred_time"):
        text += f"⏰ <b>Время:</b> {data.get('preferred_time')}\n"
    
    if data.get("coaching_topic"):
        text += f"📚 <b>Тема обучения:</b> {data.get('coaching_topic')}\n"
    
    if data.get("coaching_hours"):
        text += f"⏱️ <b>Часов:</b> {data.get('coaching_hours')}\n"
    
    if data.get("contact_info"):
        text += f"📞 <b>Контакты:</b> {data.get('contact_info')}\n"
    
    if data.get("details"):
        text += f"📝 <b>Детали:</b> {data.get('details')}\n"
    
    text += f"\n💰 <b>Стоимость:</b> {total_cost:.0f} {currency}"
    
    return text

@router.callback_query(F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    """Подтверждение заказа"""
    logger.info(f"Пользователь @{call.from_user.username} подтвердил заказ")
    
    data = await state.get_data()
    
    # Подготавливаем данные для сохранения
    order_data = {
        "user_id": data.get("user_id"),
        "service_type": data.get("service_type"),
        "boost_type": data.get("boost_type"),
        "region": data.get("region"),
        "current_rank": data.get("current_rank"),
        "target_rank": data.get("target_rank"),
        "current_mythic_stars": data.get("current_mythic_stars"),
        "target_mythic_stars": data.get("target_mythic_stars"),
        "lane": data.get("lane"),
        "heroes_mains": data.get("heroes_mains"),
        "game_id": data.get("game_id"),
        "contact_info": data.get("contact_info"),
        "base_cost": data.get("base_cost"),
        "total_cost": data.get("total_cost"),
        "currency": data.get("currency"),
        "details": data.get("details"),
        "preferred_time": data.get("preferred_time"),
        "coaching_topic": data.get("coaching_topic"),
        "coaching_hours": data.get("coaching_hours")
    }
    
    # Парсим данные аккаунта если есть
    if data.get("account_data"):
        account_data = data.get("account_data")
        lines = account_data.split('\n')
        for line in lines:
            if 'логин:' in line.lower():
                order_data["game_login"] = line.split(':', 1)[1].strip()
            elif 'пароль:' in line.lower():
                order_data["game_password"] = line.split(':', 1)[1].strip()
    
    try:
        # Сохраняем заказ в базу
        order = await create_order(order_data)
        
        await call.message.edit_text(
            f"✅ <b>Заказ создан!</b>\n\n"
            f"🆔 <b>Номер заказа:</b> <code>{order.order_id}</code>\n"
            f"💰 <b>Стоимость:</b> {order.total_cost:.0f} {order.currency}\n"
            f"📊 <b>Статус:</b> Ожидает подтверждения\n\n"
            f"Ваш заказ отправлен на рассмотрение.\n"
            f"Ожидайте подтверждения от админа в ближайшее время\n\n"
            f"📦 Посмотреть заказ можно в разделе «Мои заказы»",
            parse_mode="HTML"
        )
        
        logger.info(f"Заказ {order.order_id} создан пользователем @{call.from_user.username}")
        
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}")
        await call.message.edit_text(
            "❌ <b>Ошибка создания заказа</b>\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode="HTML"
        )
    
    await state.clear()
    await call.answer("Заказ создан!")

# Обработчики отмены
@router.callback_query(F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    """Универсальная отмена создания заказа"""
    logger.info(f"Пользователь @{call.from_user.username} отменил создание заказа")
    
    await state.clear()
    
    await call.message.edit_text(
        "❌ <b>Создание заказа отменено</b>\n\n"
        "Вы можете начать заново в любое время.",
        parse_mode="HTML"
    )
    
    await call.answer("Заказ отменен")

@router.message(F.text.in_(["❌ Отмена", "Отмена", "отмена"]))
async def cancel_order_text(message: Message, state: FSMContext):
    """Отмена заказа через текстовое сообщение"""
    logger.info(f"Пользователь @{message.from_user.username} отменил создание заказа текстом")
    
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    # Получаем текущее состояние
    current_state = await state.get_state()
    
    # Если пользователь не в процессе создания заказа
    if not current_state or not current_state.startswith("OrderStates"):
        await message.answer(
            "ℹ️ Вы не создаете заказ в данный момент.",
            parse_mode="HTML"
        )
        return
    
    # Очищаем состояние
    await state.clear()
    
    await message.answer(
        "❌ <b>Создание заказа отменено</b>\n\n"
        "Вы можете начать заново в любое время.",
        parse_mode="HTML"
    )