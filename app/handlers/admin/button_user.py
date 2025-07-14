import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from app.keyboards.admin.admin_menu import admin_menu_keyboard
from app.keyboards.admin.users_pagination import (
    users_pagination_keyboard,
    users_search_keyboard,
    user_profile_keyboard)
from app.utils.roles import admin_only
from app.database.crud import (
    get_users_page,
    count_users,
    count_users_by_role,
    search_users,
    get_user_by_tg_id,
    update_user_balance,
    update_user_bonus_balance,
    update_user_role,
    create_booster_account,
    set_booster_status
)
from app.database.session import get_session
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.states.admin_states import AdminStates
from app.utils.currency import get_active_balance
from app.utils.user import format_user_profile
router = Router()
logger = logging.getLogger(__name__)

# --- ФУНКЦИОНАЛ ДЛЯ КНОПКИ: ПОЛЬЗОВАТЕЛИ ---
USERS_PER_PAGE = 5  # Количество пользователей на одной странице



# --- Админ-панель ---
@router.message(Command("admin"))
@admin_only
async def admin_panel(message: Message):
    logger.info(f"Админ @{message.from_user.username} открыл админ-панель")
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard())

@router.message(F.text == "👥 Пользователи")
@admin_only
async def admin_users(message: Message):
    logger.info(f"Админ @{message.from_user.username} открыл список пользователей")
    """Показать первую страницу пользователей с общей статистикой."""
    page = 1
    total_users = await count_users()
    total_clients = await count_users_by_role("user")
    total_boosters = await count_users_by_role("booster")
    total_pages = max(1, (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    users = await get_users_page(offset=0, limit=USERS_PER_PAGE)
    text = (
        f"<b>Всего пользователей:</b> {total_users}\n"
        f"<b>Клиентов:</b> {total_clients}\n"
        f"<b>Бустеров:</b> {total_boosters}\n\n"
        f"<b>Список пользователей:</b>"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=users_pagination_keyboard(users, page, total_pages)
    )

@router.callback_query(F.data.startswith("users_page:"))
@admin_only
async def users_page_callback(call: CallbackQuery):
    logger.info(f"Админ @{call.from_user.username} листает пользователей, страница {call.data}")
    """Обработка пагинации пользователей."""
    page = int(call.data.split(":")[1])
    total_users = await count_users()
    total_pages = max(1, (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    offset = (page - 1) * USERS_PER_PAGE
    users = await get_users_page(offset=offset, limit=USERS_PER_PAGE)
    total_clients = await count_users_by_role("user")
    total_boosters = await count_users_by_role("booster")
    text = (
        f"<b>Всего пользователей:</b> {total_users}\n"
        f"<b>Клиентов:</b> {total_clients}\n"
        f"<b>Бустеров:</b> {total_boosters}\n\n"
        f"<b>Список пользователей:</b>"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=users_pagination_keyboard(users, page, total_pages)
    )
    await call.answer()

@router.callback_query(F.data == "users_search")
@admin_only
async def users_search_start(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} начал поиск пользователя")
    """Запрос поиска пользователя."""
    await call.message.delete()
    await call.message.answer("Введите username или ID пользователя для поиска:")
    await state.set_state(AdminStates.waiting_for_query)
    await call.answer()

@router.message(AdminStates.waiting_for_query)
@admin_only
async def users_search_process(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} ищет пользователя: {message.text}")
    """Обработка поиска пользователя."""
    query = message.text.strip().lstrip("@")
    users = await search_users(query)
    if not users:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="users_page:1")]
            ]
        )
        await message.answer("Пользователь не найден.", reply_markup=keyboard)
    else:
        await message.answer(
            "<b>Результаты поиска:</b>",
            parse_mode="HTML",
            reply_markup=users_search_keyboard(users)
        )
    await state.clear()

    
@router.callback_query(F.data.startswith("user_info:"))
@admin_only
async def user_info_from_list(call: CallbackQuery):
    parts = call.data.split(":")
    tg_id = int(parts[1])
    request_id = parts[2] if len(parts) > 2 else None
    user = await get_user_by_tg_id(tg_id)
    if not user:
        await call.answer("Пользователь не найден.", show_alert=True)
        return
    await call.message.delete()
    if request_id:
        from app.keyboards.admin.payments import back_to_payment_keyboard
        await call.message.answer(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=back_to_payment_keyboard(request_id, user)
        )
    else:
        from app.keyboards.admin.users_pagination import user_profile_keyboard
        await call.message.answer(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=user_profile_keyboard(user)
        )
    await call.answer()

@router.callback_query(F.data.startswith("user_ban:"))
@admin_only
async def user_ban_callback(call: CallbackQuery):
    parts = call.data.split(":")
    tg_id = int(parts[1])
    request_id = parts[2] if len(parts) > 2 else None
    user = await get_user_by_tg_id(tg_id)
    if user.role == "admin":
        await call.answer("Нельзя забанить администратора!", show_alert=True)
        return
    if user.role == "banned":
        await call.answer("Пользователь уже забанен.", show_alert=True)
        return
    await update_user_role(tg_id, "banned")
    user = await get_user_by_tg_id(tg_id)
    if request_id:
        from app.keyboards.admin.payments import back_to_payment_keyboard
        await call.message.edit_text(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=back_to_payment_keyboard(request_id, user)
        )
    else:
        from app.keyboards.admin.users_pagination import user_profile_keyboard
        await call.message.edit_text(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=user_profile_keyboard(user)
        )
    await call.answer()

@router.callback_query(F.data.startswith("user_unban:"))
@admin_only
async def user_unban_callback(call: CallbackQuery):
    logger.info(f"Админ @{call.from_user.username} пытается разбанить пользователя {call.data}")
    parts = call.data.split(":")
    tg_id = int(parts[1])
    request_id = parts[2] if len(parts) > 2 else None
    user = await get_user_by_tg_id(tg_id)
    if user.role != "banned":
        await call.answer("Пользователь не забанен.", show_alert=True)
        return
    await update_user_role(tg_id, "user")
    user = await get_user_by_tg_id(tg_id)  # обновляем данные
    if request_id:
        from app.keyboards.admin.payments import back_to_payment_keyboard
        await call.message.edit_text(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=back_to_payment_keyboard(request_id, user)
        )
        await call.answer("Пользователь разбанен.")
    else:
        from app.keyboards.admin.users_pagination import user_profile_keyboard
        await call.message.edit_text(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=user_profile_keyboard(user)
        )
        await call.answer("Пользователь разбанен.")

@router.callback_query(F.data.startswith("user_balance:"))
@admin_only
async def user_balance_callback(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    tg_id = int(parts[1])
    request_id = parts[2] if len(parts) > 2 else None
    await state.update_data(balance_tg_id=tg_id, request_id=request_id)
    await call.message.delete()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"user_info:{tg_id}:{request_id}" if request_id else f"user_info:{tg_id}")]
        ]
    )
    await call.message.answer(
        "Введите новый баланс:",
        reply_markup=keyboard
    )
    await state.set_state(AdminStates.waiting_for_balance)
    await call.answer()

@router.message(AdminStates.waiting_for_balance)
@admin_only
async def set_user_balance(message: Message, state: FSMContext):
    data = await state.get_data()
    tg_id = data.get("balance_tg_id")
    request_id = data.get("request_id")
    try:
        new_balance = int(message.text)
    except ValueError:
        await message.answer("Введите корректное число!")
        return
    await update_user_balance(tg_id, new_balance)
    user = await get_user_by_tg_id(tg_id)
    if request_id:
        from app.keyboards.admin.payments import back_to_payment_keyboard
        await message.answer(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=back_to_payment_keyboard(request_id, user)
        )
    else:
        from app.keyboards.admin.users_pagination import user_profile_keyboard
        await message.answer(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=user_profile_keyboard(user)
        )
    await state.clear()

@router.callback_query(F.data.startswith("user_bonus:"))
@admin_only
async def user_bonus_callback(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    tg_id = int(parts[1])
    request_id = parts[2] if len(parts) > 2 else None
    await state.update_data(bonus_tg_id=tg_id, request_id=request_id)
    await call.message.delete()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"user_info:{tg_id}:{request_id}" if request_id else f"user_info:{tg_id}")]
        ]
    )
    await call.message.answer(
        "Введите новое значение бонусного баланса:",
        reply_markup=keyboard
    )
    await state.set_state(AdminStates.waiting_for_bonus)
    await call.answer()

@router.message(AdminStates.waiting_for_bonus)
@admin_only
async def set_user_bonus_balance(message: Message, state: FSMContext):
    data = await state.get_data()
    tg_id = data.get("bonus_tg_id")
    request_id = data.get("request_id")
    try:
        new_bonus = int(message.text)
    except ValueError:
        await message.answer("Введите корректное число!")
        return
    await update_user_bonus_balance(tg_id, new_bonus)
    user = await get_user_by_tg_id(tg_id)
    if request_id:
        from app.keyboards.admin.payments import back_to_payment_keyboard
        await message.answer(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=back_to_payment_keyboard(request_id, user)
        )
    else:
        from app.keyboards.admin.users_pagination import user_profile_keyboard
        await message.answer(
            format_user_profile(user),
            parse_mode="HTML",
            reply_markup=user_profile_keyboard(user)
        )
    await state.clear()

@router.callback_query(F.data.startswith("user_info:"))
@admin_only
async def back_to_profile_from_balance(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} вернулся к профилю пользователя {call.data}")
    """Возврат к профилю пользователя из ввода баланса."""
    tg_id = int(call.data.split(":")[1])
    user = await get_user_by_tg_id(tg_id)
    await state.clear()
    await call.message.edit_text(
        format_user_profile(user),
        parse_mode="HTML",
        reply_markup=user_profile_keyboard(user)
    )
    await call.answer()

@router.callback_query(F.data == "users_broadcast")
@admin_only
async def users_broadcast_start(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} начал рассылку всем пользователям")
    """Запрос текста для рассылки."""
    await call.message.delete()
    await call.message.answer("Введите текст рассылки, который получат все пользователи:")
    await state.set_state(AdminStates.waiting_for_broadcast)
    await call.answer()

@router.message(AdminStates.waiting_for_broadcast)
@admin_only
async def users_broadcast_process(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} отправляет рассылку всем: {message.text or '[фото]'}")
    """Отправка рассылки всем пользователям с прогрессом и итоговой статистикой. Поддержка фото и текста."""
    users = await get_users_page(offset=0, limit=1000000)
    total = len(users)
    delivered = 0
    failed = 0

    # Сообщаем администратору о начале рассылки
    progress_msg = await message.answer(f"📢 Рассылка началась...\nВсего пользователей: {total}")

    # Определяем, что отправлять: фото или текст
    is_photo = message.photo and len(message.photo) > 0
    text = message.caption if is_photo else message.text

    for idx, user in enumerate(users, start=1):
        if user.tg_id == message.from_user.id:
            continue
        try:
            if is_photo:
                await message.bot.send_photo(
                    user.tg_id,
                    photo=message.photo[-1].file_id,
                    caption=text
                )
            else:
                await message.bot.send_message(user.tg_id, text)
            delivered += 1
        except Exception:
            failed += 1

        if idx % 5 == 0 or idx == total:
            try:
                await progress_msg.edit_text(
                    f"📢 Рассылка идёт...\n"
                    f"Отправлено: {delivered}\n"
                    f"Не доставлено: {failed}\n"
                    f"Всего: {total}"
                )
            except Exception:
                pass

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="users_page:1")]
        ]
    )
    await progress_msg.edit_text(
        f"✅ Рассылка завершена!\n"
        f"Доставлено: {delivered}\n"
        f"Не доставлено: {failed}\n"
        f"Всего пользователей: {total}",
        reply_markup=keyboard
    )
    await state.clear()

@router.callback_query(F.data == "boosters_broadcast")
@admin_only
async def boosters_broadcast_start(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} начал рассылку бустерам")
    """Запрос текста для рассылки бустерам."""
    await call.message.delete()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
        ]
    )
    await call.message.answer("Введите текст или фото для рассылки всем бустерам:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_boosters_broadcast)
    await call.answer()

@router.message(AdminStates.waiting_for_boosters_broadcast)
@admin_only
async def boosters_broadcast_process(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username} отправляет рассылку бустерам: {message.text or '[фото]'}")
    """Отправка рассылки всем бустерам с прогрессом и итоговой статистикой. Поддержка фото и текста."""
    # Получаем только бустеров
    boosters = await search_users("booster")  # или отдельная функция для получения всех бустеров
    total = len(boosters)
    delivered = 0
    failed = 0

    progress_msg = await message.answer(f"📢 Рассылка бустерам началась...\nВсего бустеров: {total}")

    is_photo = message.photo and len(message.photo) > 0
    text = message.caption if is_photo else message.text

    for idx, user in enumerate(boosters, start=1):
        if user.tg_id == message.from_user.id:
            continue
        try:
            if is_photo:
                await message.bot.send_photo(
                    user.tg_id,
                    photo=message.photo[-1].file_id,
                    caption=text
                )
            else:
                await message.bot.send_message(user.tg_id, text)
            delivered += 1
        except Exception:
            failed += 1

        if idx % 5 == 0 or idx == total:
            try:
                await progress_msg.edit_text(
                    f"📢 Рассылка идёт...\n"
                    f"Отправлено: {delivered}\n"
                    f"Не доставлено: {failed}\n"
                    f"Всего: {total}"
                )
            except Exception:
                pass

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="users_page:1")]
        ]
    )
    await progress_msg.edit_text(
        f"✅ Рассылка бустерам завершена!\n"
        f"Доставлено: {delivered}\n"
        f"Не доставлено: {failed}\n"
        f"Всего бустеров: {total}",
        reply_markup=keyboard
    )
    await state.clear()


# --- Отмена рассылки ---
@router.callback_query(F.data == "cancel_broadcast")
@admin_only
async def cancel_broadcast(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username} отменил рассылку")
    """Отмена рассылки и возврат к списку пользователей."""
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="users_page:1")]
        ]
    )
    await call.message.edit_text(
        "❌ Рассылка отменена.",
        reply_markup=keyboard
    )
    await call.answer()

@router.callback_query(F.data.startswith("user_set_booster:"))
@admin_only
async def user_set_booster_callback(call: CallbackQuery):
    """Назначить пользователя бустером."""
    logger.info(f"Админ @{call.from_user.username} назначает бустером пользователя {call.data}")
    tg_id = int(call.data.split(":")[1])
    await update_user_role(tg_id, "booster")
    user = await get_user_by_tg_id(tg_id)
    async with get_session() as session:
        await create_booster_account(user.id, user.username, session)
        await set_booster_status(user.id, "active", session)
    await call.message.edit_text(
        format_user_profile(user),
        parse_mode="HTML",
        reply_markup=user_profile_keyboard(user)
    )
    await call.answer("Пользователь назначен бустером.")

@router.callback_query(F.data.startswith("user_unset_booster:"))
@admin_only
async def user_unset_booster_callback(call: CallbackQuery):
    """Снять роль бустера с пользователя."""
    logger.info(f"Админ @{call.from_user.username} снимает роль бустера с пользователя {call.data}")
    tg_id = int(call.data.split(":")[1])
    await update_user_role(tg_id, "user")
    user = await get_user_by_tg_id(tg_id)
    async with get_session() as session:
        await set_booster_status(user.id, "inactive", session)
    await call.message.edit_text(
        format_user_profile(user),
        parse_mode="HTML",
        reply_markup=user_profile_keyboard(user)
    )
    await call.answer("Роль бустера снята.")