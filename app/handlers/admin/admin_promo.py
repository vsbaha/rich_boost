from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
from app.database.models import PromoCode
from app.database.db import AsyncSessionLocal
from app.utils.roles import admin_only
from app.states.admin_states import PromoCreateStates
from sqlalchemy import select
from app.keyboards.admin.promo import (
    promo_type_keyboard,
    promo_currency_keyboard,
    promo_onetime_keyboard,
    promo_confirm_keyboard,
    cancel_keyboard,
    promo_menu_keyboard,
    promo_list_keyboard,
    promo_manage_keyboard
)
import logging

logger = logging.getLogger(__name__)

router = Router()

PROMOS_PER_PAGE = 7

async def delete_last_bot_message(message, state):
    data = await state.get_data()
    if data.get("last_bot_msg"):
        try:
            await message.bot.delete_message(message.chat.id, data["last_bot_msg"])
        except Exception:
            pass

@router.message(F.text.lower() == "🎁 промокоды")
@admin_only
async def promo_main_menu(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} открыл меню промокодов")
    msg = await message.answer("Выберите действие:", reply_markup=promo_menu_keyboard())
    await state.update_data(last_bot_msg=msg.message_id)

@router.callback_query(F.data == "promo_create")
@admin_only
async def promo_create_entry(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} начал создание промокода")
    await call.message.edit_text("🔤 Введите промокод (только латиница/цифры):", reply_markup=cancel_keyboard())
    await state.set_state(PromoCreateStates.waiting_for_code)

@router.callback_query(F.data == "promo_active")
@admin_only
async def promo_active_list(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} открыл список активных промокодов")
    await show_promo_page(call.message, state, page=1)

async def show_promo_page(event, state, page=1, search_query=None):
    # лог не нужен, т.к. вызывается из других функций
    async with AsyncSessionLocal() as session:
        if search_query:
            query = select(PromoCode).where(PromoCode.code.ilike(f"%{search_query}%"))
        else:
            query = select(PromoCode).where(PromoCode.is_active == True)
        promos = (await session.execute(query.order_by(PromoCode.id.desc()))).scalars().all()
    total = len(promos)
    total_pages = max(1, (total + PROMOS_PER_PAGE - 1) // PROMOS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PROMOS_PER_PAGE
    end = start + PROMOS_PER_PAGE
    page_promos = promos[start:end]
    if search_query:
        text = "Результаты поиска:" if promos else "Промокоды не найдены."
    else:
        text = "🟢 Активные промокоды:" if promos else "Нет активных промокодов."
    kb = promo_list_keyboard(page_promos, page, total_pages) if promos else promo_menu_keyboard()

    try:
        await event.edit_text(text, reply_markup=kb)
    except Exception:
        await event.answer(text, reply_markup=kb)
    await state.update_data(promo_search=search_query or "")

@router.callback_query(F.data.startswith("promo_page:"))
@admin_only
async def promo_page_nav(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} листает страницы промокодов (страница {call.data.split(':')[1]})")
    page = call.data.split(":")[1]
    if page == "cur":
        await call.answer()
        return
    page = int(page)
    data = await state.get_data()
    search_query = data.get("promo_search")
    await show_promo_page(call.message, state, page=page, search_query=search_query)

@router.callback_query(F.data == "promo_search")
@admin_only
async def promo_search_start(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} начал поиск промокода")
    await call.message.edit_text("Введите часть промокода для поиска:", reply_markup=cancel_keyboard())
    await state.set_state(PromoCreateStates.waiting_for_search)

@router.message(PromoCreateStates.waiting_for_search)
@admin_only
async def promo_search_query(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} ищет промокод по запросу: {message.text.strip()}")
    try:
        await message.delete()
    except Exception:
        pass
    await delete_last_bot_message(message, state)
    query = message.text.strip()
    if not query:
        msg = await message.answer("Введите часть промокода для поиска.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return
    await show_promo_page(message, state, page=1, search_query=query)
    await state.clear()

@router.callback_query(F.data == "promo_cancel")
@admin_only
async def promo_cancel_callback(call: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == PromoCreateStates.waiting_for_search.state:
        logger.info(f"Админ @{call.from_user.username} отменил поиск промокода")
        await call.message.edit_text("Поиск промокода отменён.", reply_markup=promo_menu_keyboard())
    else:
        logger.info(f"Админ @{call.from_user.username} отменил создание промокода")
        await call.message.edit_text("Создание промокода отменено.", reply_markup=promo_menu_keyboard())
    await state.clear()

@router.message(PromoCreateStates.waiting_for_code)
@admin_only
async def promo_code_step(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} вводит код промокода: {message.text.strip()}")
    try:
        await message.delete()
    except Exception:
        pass
    await delete_last_bot_message(message, state)
    if not message.text:
        msg = await message.answer("Пожалуйста, отправьте промокод текстом.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return
    code = message.text.strip().upper()
    if not code.isalnum():
        msg = await message.answer("Промокод должен содержать только латиницу и цифры.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return
    async with AsyncSessionLocal() as session:
        exists = await session.execute(
            select(PromoCode).where(PromoCode.code == code)
        )
        if exists.scalar_one_or_none():
            msg = await message.answer("Такой промокод уже существует. Введите другой.", reply_markup=cancel_keyboard())
            await state.update_data(last_bot_msg=msg.message_id)
            return
    await state.update_data(code=code)
    msg = await message.answer("Выберите тип промокода:", reply_markup=promo_type_keyboard())
    await state.update_data(last_bot_msg=msg.message_id)

@router.callback_query(F.data.startswith("promo_type:"))
@admin_only
async def promo_type_callback(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} выбрал тип промокода: {call.data.split(':')[1]}")
    promo_type = call.data.split(":")[1]
    await state.update_data(type=promo_type)
    await call.message.edit_text(
        "💰 Введите значение (процент для скидки или сумму для бонуса):",
        reply_markup=cancel_keyboard()
    )
    await state.update_data(last_bot_msg=call.message.message_id)
    await state.set_state(PromoCreateStates.waiting_for_value)

@router.message(PromoCreateStates.waiting_for_value)
@admin_only
async def promo_value_step(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} вводит значение промокода: {message.text.strip()}")
    try:
        await message.delete()
    except Exception:
        pass
    await delete_last_bot_message(message, state)
    if not message.text:
        msg = await message.answer("Пожалуйста, отправьте число текстом.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return
    try:
        value = float(message.text.replace(",", "."))
    except Exception:
        msg = await message.answer("Введите число.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return

    data = await state.get_data()
    if value <= 0:
        msg = await message.answer("Значение должно быть положительным числом.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return

    if data.get("type") == "discount":
        if not (1 <= value <= 100):
            msg = await message.answer("Для скидки процент должен быть от 1 до 100.", reply_markup=cancel_keyboard())
            await state.update_data(last_bot_msg=msg.message_id)
            return

    await state.update_data(value=value)
    if data["type"] == "bonus":
        msg = await message.answer("Выберите валюту бонуса:", reply_markup=promo_currency_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        await state.set_state(PromoCreateStates.waiting_for_currency)
    else:
        await state.update_data(currency=None)
        msg = await message.answer("Выберите тип промокода:", reply_markup=promo_onetime_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        await state.set_state(PromoCreateStates.waiting_for_one_time)

@router.callback_query(F.data.startswith("promo_currency:"))
@admin_only
async def promo_currency_callback(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} выбрал валюту бонуса: {call.data.split(':')[1]}")
    currency = call.data.split(":")[1]
    await state.update_data(currency=currency)
    await call.message.edit_text("Выберите тип промокода:", reply_markup=promo_onetime_keyboard())
    await state.set_state(PromoCreateStates.waiting_for_one_time)

@router.callback_query(F.data.startswith("promo_onetime:"))
@admin_only
async def promo_onetime_callback(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} выбрал одноразовость промокода: {call.data.split(':')[1]}")
    is_one_time = call.data.split(":")[1] == "yes"
    await state.update_data(is_one_time=is_one_time)
    if not is_one_time:
        await call.message.edit_text("🔢 Максимальное число активаций? (число или 0 для безлимитного)", reply_markup=cancel_keyboard())
        await state.set_state(PromoCreateStates.waiting_for_max_activations)
    else:
        await state.update_data(max_activations=1)
        await call.message.edit_text("📅 Срок действия? (дд.мм.гггг или дд.мм.гггг чч:мм или 'нет')", reply_markup=cancel_keyboard())
        await state.set_state(PromoCreateStates.waiting_for_expires)

@router.message(PromoCreateStates.waiting_for_max_activations)
@admin_only
async def promo_max_activations_step(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} вводит лимит активаций: {message.text.strip()}")
    try:
        await message.delete()
    except Exception:
        pass
    await delete_last_bot_message(message, state)
    if not message.text:
        msg = await message.answer("Пожалуйста, отправьте число текстом.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return
    try:
        max_activations = int(message.text)
        if max_activations <= 0:
            max_activations = None
    except Exception:
        msg = await message.answer("Введите число.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return
    await state.update_data(max_activations=max_activations)
    msg = await message.answer("📅 Срок действия? (дд.мм.гггг или дд.мм.гггг чч:мм или 'нет')", reply_markup=cancel_keyboard())
    await state.update_data(last_bot_msg=msg.message_id)
    await state.set_state(PromoCreateStates.waiting_for_expires)

@router.message(PromoCreateStates.waiting_for_expires)
@admin_only
async def promo_expires_step(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} вводит срок действия промокода: {message.text.strip()}")
    try:
        await message.delete()
    except Exception:
        pass
    await delete_last_bot_message(message, state)
    if not message.text:
        msg = await message.answer("Пожалуйста, отправьте дату текстом.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return
    text = message.text.strip().lower()
    if text == "нет":
        expires = None
    else:
        expires = None
        for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y"):
            try:
                expires = datetime.strptime(text, fmt)
                break
            except Exception:
                continue
        if not expires:
            msg = await message.answer("Введите дату в формате дд.мм.гггг или дд.мм.гггг чч:мм, либо 'нет'.", reply_markup=cancel_keyboard())
            await state.update_data(last_bot_msg=msg.message_id)
            return
        now = datetime.now()
        if expires < now:
            msg = await message.answer("Дата окончания не может быть раньше текущей даты и времени.", reply_markup=cancel_keyboard())
            await state.update_data(last_bot_msg=msg.message_id)
            return
    await state.update_data(expires_at=expires)
    msg = await message.answer("💬 Комментарий к промокоду (или '-' если не нужен):", reply_markup=cancel_keyboard())
    await state.update_data(last_bot_msg=msg.message_id)
    await state.set_state(PromoCreateStates.waiting_for_comment)

@router.message(PromoCreateStates.waiting_for_comment)
@admin_only
async def promo_comment_step(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} вводит комментарий к промокоду: {message.text.strip()}")
    try:
        await message.delete()
    except Exception:
        pass
    await delete_last_bot_message(message, state)
    if not message.text:
        msg = await message.answer("Пожалуйста, отправьте комментарий текстом или '-' если не нужен.", reply_markup=cancel_keyboard())
        await state.update_data(last_bot_msg=msg.message_id)
        return
    comment = message.text.strip()
    if comment == "-":
        comment = None
    await state.update_data(comment=comment)
    data = await state.get_data()

    # Форматирование для вывода
    if data["type"] == "bonus":
        value_str = f"{data['value']} {data.get('currency','')}"
    else:
        value_str = f"{data['value']}%"

    max_activations = data.get('max_activations')
    if max_activations in (None, 0):
        max_activations_str = "Безлимитно"
    else:
        max_activations_str = str(max_activations)

    expires_at = data.get('expires_at')
    if not expires_at:
        expires_str = "Без срока"
    elif isinstance(expires_at, str):
        expires_str = expires_at
    elif isinstance(expires_at, datetime):
        expires_str = expires_at.strftime("%d.%m.%Y %H:%M") if (expires_at.hour or expires_at.minute) else expires_at.strftime("%d.%m.%Y")
    else:
        expires_str = str(expires_at)

    comment_str = comment or "-"

    text = (
        f"<b>Промокод:</b> {data['code']}\n"
        f"<b>Тип:</b> {data['type']}\n"
        f"<b>Значение:</b> {value_str}\n"
        f"<b>Одноразовый:</b> {'Да' if data['is_one_time'] else 'Нет'}\n"
        f"<b>Лимит активаций:</b> {max_activations_str}\n"
        f"<b>Срок действия:</b> {expires_str}\n"
        f"<b>Комментарий:</b> {comment_str if comment_str != '-' else 'Без комментария'}\n\n"
        "Подтвердить создание промокода?"
    )
    msg = await message.answer(text, parse_mode="HTML", reply_markup=promo_confirm_keyboard())
    await state.update_data(last_bot_msg=msg.message_id)
    await state.set_state(PromoCreateStates.confirm)

@router.callback_query(F.data.startswith("promo_confirm:"))
@admin_only
async def promo_confirm_callback(call: CallbackQuery, state: FSMContext):
    answer = call.data.split(":")[1]
    if answer != "yes":
        logger.info(f"Админ @{call.from_user.username} отменил создание промокода на этапе подтверждения")
        await call.message.edit_text("Создание промокода отменено.")
        await state.clear()
        return
    data = await state.get_data()
    expires_at = data.get("expires_at")
    # Получаем регион админа
    from app.database.crud import get_user_by_tg_id
    admin_user = await get_user_by_tg_id(call.from_user.id)
    region = getattr(admin_user, "region", None) if admin_user else None
    # Карта регионов в таймзоны
    region_tz = {
        "🇰🇬 КР": "Asia/Bishkek",
        "kg": "Asia/Bishkek",
        "🇰🇿 КЗ": "Asia/Almaty",
        "kz": "Asia/Almaty",
        "🇷🇺 РУ": "Europe/Moscow",
        "ru": "Europe/Moscow",
    }
    import pytz
    tz_name = region_tz.get(region, "Asia/Bishkek")
    tz = pytz.timezone(tz_name)
    if isinstance(expires_at, datetime):
        expires_at = expires_at.replace(microsecond=0)
        if expires_at.tzinfo is None:
            # expires_at введён как локальное время админа, переводим в UTC
            local_dt = tz.localize(expires_at)
            expires_at = local_dt.astimezone(pytz.utc)
    async with AsyncSessionLocal() as session:
        promo = PromoCode(
            code=data["code"],
            type=data["type"],
            value=data["value"],
            currency=data.get("currency"),
            is_one_time=data["is_one_time"],
            max_activations=data.get("max_activations"),
            expires_at=expires_at,
            comment=data.get("comment"),
        )
        session.add(promo)
        await session.commit()
    logger.info(f"Админ @{call.from_user.username} создал промокод {data['code']}")
    await call.message.edit_text("Промокод успешно создан!", reply_markup=promo_menu_keyboard())
    await state.clear()

@router.callback_query(F.data.startswith("promo_manage:"))
@admin_only
async def promo_manage_panel(call: CallbackQuery, state: FSMContext):
    promo_id = int(call.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        promo = await session.get(PromoCode, promo_id)
    if not promo:
        await call.answer("Промокод не найден", show_alert=True)
        return
    logger.info(f"Админ @{call.from_user.username} открыл управление промокодом {promo.code} (id={promo.id})")
    text = (
        f"<b>Промокод:</b> {promo.code}\n"
        f"<b>Тип:</b> {promo.type}\n"
        f"<b>Значение:</b> {promo.value} {promo.currency or '%'}\n"
        f"<b>Одноразовый:</b> {'Да' if promo.is_one_time else 'Нет'}\n"
        f"<b>Лимит активаций:</b> {promo.max_activations or 'Безлимитно'}\n"
        f"<b>Срок действия:</b> {promo.expires_at.strftime('%d.%m.%Y %H:%M') if promo.expires_at else 'Без срока'}\n"
        f"<b>Комментарий:</b> {promo.comment or '-'}\n"
        f"<b>Статус:</b> {'🟢 Активен' if promo.is_active else '🧊 Заморожен'}"
    )
    await call.message.edit_text(
        text, parse_mode="HTML", reply_markup=promo_manage_keyboard(promo)
    )

@router.callback_query(F.data.startswith("promo_toggle:"))
@admin_only
async def promo_toggle_status(call: CallbackQuery, state: FSMContext):
    promo_id = int(call.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        promo = await session.get(PromoCode, promo_id)
        if not promo:
            await call.answer("Промокод не найден", show_alert=True)
            return
        promo.is_active = not promo.is_active
        await session.commit()
    logger.info(f"Админ @{call.from_user.username} изменил статус промокода {promo.code} (id={promo.id}) на {'активен' if promo.is_active else 'заморожен'}")
    await call.answer("Статус изменён")
    await promo_manage_panel(call, state)

@router.callback_query(F.data.startswith("promo_delete:"))
@admin_only
async def promo_delete(call: CallbackQuery, state: FSMContext):
    promo_id = int(call.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        promo = await session.get(PromoCode, promo_id)
        if not promo:
            await call.answer("Промокод не найден", show_alert=True)
            return
        logger.info(f"Админ @{call.from_user.username} удалил промокод {promo.code} (id={promo.id})")
        await session.delete(promo)
        await session.commit()
    await call.answer("Промокод удалён")
    await promo_active_list(call, state)

@router.callback_query(F.data == "promo_menu")
@admin_only
async def promo_menu_back(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} вернулся в меню промокодов")
    await call.message.edit_text("Выберите действие:", reply_markup=promo_menu_keyboard())
    await state.update_data(last_bot_msg=call.message.message_id)
