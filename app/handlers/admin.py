import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from app.keyboards.admin.admin_menu import admin_menu_keyboard
from app.keyboards.admin.users_pagination import users_pagination_keyboard, users_search_keyboard, user_profile_keyboard
from app.utils.roles import admin_only
from app.database.crud import get_users_page, count_users, count_users_by_role, search_users, get_user_by_tg_id, update_user_balance
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.states.admin_states import AdminStates

router = Router()
logger = logging.getLogger(__name__)

USERS_PER_PAGE = 5

@router.message(Command("admin"))
@admin_only
async def admin_panel(message: Message):
    logger.info(f"Админ @{message.from_user.username} открыл админ-панель")
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard())

@router.message(F.text == "👥 Пользователи")
@admin_only
async def admin_users(message: Message):
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

@router.message(F.text == "📦 Все заказы")
@admin_only
async def admin_orders(message: Message):
    await message.answer("Здесь будет список всех заказов.")

@router.message(F.text == "🎯 Настройки")
@admin_only
async def admin_settings(message: Message):
    await message.answer("Здесь будут настройки.")

@router.message(F.text == "📞 Поддержка")
@admin_only
async def admin_support(message: Message):
    await message.answer("Здесь будет связь с поддержкой.")

@router.callback_query(F.data == "users_search")
@admin_only
async def users_search_start(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer("Введите username или ID пользователя для поиска:")
    await state.set_state(AdminStates.waiting_for_query)
    await call.answer()

@router.message(AdminStates.waiting_for_query)
@admin_only
async def users_search_process(message: Message, state: FSMContext):
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
async def user_info_callback(call: CallbackQuery):
    tg_id = int(call.data.split(":")[1])
    user = await get_user_by_tg_id(tg_id)
    if not user:
        await call.answer("Пользователь не найден.", show_alert=True)
        return
    text = (
        f"<b>Профиль пользователя</b>\n"
        f"ID: <code>{user.tg_id}</code>\n"
        f"Username: @{user.username or '—'}\n"
        f"Регион: {user.region or '—'}\n"
        f"Роль: {user.role}\n"
        f"Баланс: {user.balance}\n"
        f"Бонусный баланс: {user.bonus_balance}\n"
        f"Дата регистрации: {user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else '—'}"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=user_profile_keyboard(user)
    )
    await call.answer()

@router.callback_query(F.data.startswith("user_ban:"))
@admin_only
async def user_ban_callback(call: CallbackQuery):
    tg_id = int(call.data.split(":")[1])
    # Здесь логика смены роли на "banned"
    # await update_user_role(tg_id, "banned")
    await call.answer("Пользователь забанен (заглушка).")

@router.callback_query(F.data.startswith("user_unban:"))
@admin_only
async def user_unban_callback(call: CallbackQuery):
    tg_id = int(call.data.split(":")[1])
    # Здесь логика смены роли на "user"
    # await update_user_role(tg_id, "user")
    await call.answer("Пользователь разбанен (заглушка).")

@router.callback_query(F.data.startswith("user_balance:"))
@admin_only
async def user_balance_callback(call: CallbackQuery, state: FSMContext):
    tg_id = int(call.data.split(":")[1])
    await state.update_data(balance_tg_id=tg_id)
    await call.message.answer("Введите новое значение баланса:")
    await state.set_state(AdminStates.waiting_for_balance)
    await call.answer()

@router.message(AdminStates.waiting_for_balance)
@admin_only
async def set_user_balance(message: Message, state: FSMContext):
    data = await state.get_data()
    tg_id = data.get("balance_tg_id")
    try:
        new_balance = int(message.text)
    except ValueError:
        await message.answer("Введите корректное число!")
        return
    await update_user_balance(tg_id, new_balance)
    await message.answer(f"Баланс пользователя обновлён: {new_balance}")
    await state.clear()