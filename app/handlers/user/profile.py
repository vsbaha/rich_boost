import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.database.crud import get_user_by_tg_id, update_user_region
from app.keyboards.user.profile import user_profile_keyboard
from app.utils.currency import get_active_balance
from app.states.user_states import RegionStates
from datetime import datetime, timedelta, timezone
from app.utils.referral import get_referral_link
from app.database.models import User
from sqlalchemy.future import select
from app.database.db import AsyncSessionLocal
from app.utils.referral import get_referrals_count

router = Router()
logger = logging.getLogger(__name__)



async def get_profile_text(user, balance, bonus, currency):
    reg_date = user.created_at
    if reg_date is not None and reg_date.tzinfo is None:
        reg_date = reg_date.replace(tzinfo=timezone.utc)
    if user.region == "🇰🇬 КР":
        reg_date = reg_date + timedelta(hours=6)
    elif user.region == "🇰🇿 КЗ":
        reg_date = reg_date + timedelta(hours=5)
    elif user.region == "🇷🇺 РУ":
        reg_date = reg_date + timedelta(hours=3)

    ref_link = get_referral_link(user)
    referrals = await get_referrals_count(user.id)
    return (
        f"<b>Ваш профиль</b>\n"
        f"ID: <code>{user.tg_id}</code>\n"
        f"Username: @{user.username or '—'}\n"
        f"Регион: {user.region or '—'}\n"
        f"Баланс: {balance:.2f} {currency}\n"
        f"Бонусный баланс: {bonus:.2f} {currency}\n"
        f"Дата регистрации: {reg_date.strftime('%d.%m.%Y %H:%M') if reg_date else '—'}"
        f"\n👥 Приглашено друзей: {len(referrals)}"
        f"\n🔗 Ваша ссылка: {ref_link}"
    )


@router.message(F.text == "👤 Профиль")
async def user_profile(message: Message):
    logger.info(f"Пользователь @{message.from_user.username} открыл профиль")
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        logger.warning(f"Профиль не найден для пользователя {message.from_user.id}")
        await message.answer("Профиль не найден. Напишите команду /start для регистрации." )
        return
    balance, bonus, currency = get_active_balance(user)
    text = await get_profile_text(user, balance, bonus, currency)
    await message.answer(text, parse_mode="HTML", reply_markup=user_profile_keyboard())

@router.callback_query(F.data == "user_change_region")
async def user_change_region(call: CallbackQuery, state: FSMContext):
    """Запрос нового региона у пользователя."""
    logger.info(f"Пользователь @{call.from_user.username} инициировал смену региона")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇰🇬 КР", callback_data="set_region:🇰🇬 КР")],
            [InlineKeyboardButton(text="🇷🇺 РУ", callback_data="set_region:🇷🇺 РУ")],
            [InlineKeyboardButton(text="🇰🇿 КЗ", callback_data="set_region:🇰🇿 КЗ")],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="profile_cancel")]
        ]
    )
    await call.message.edit_text("Выберите новый регион:", reply_markup=keyboard)
    await state.set_state(RegionStates.waiting_for_region)
    await call.answer()


@router.callback_query(F.data.startswith("set_region:"))
async def set_user_region(call: CallbackQuery, state: FSMContext):
    """Устанавливает новый регион (балансы не конвертируются, у каждого региона свой счет)."""
    new_region = call.data.split(":", 1)[1]
    user = await get_user_by_tg_id(call.from_user.id)
    old_region = user.region
    logger.info(f"Пользователь @{call.from_user.username} меняет регион с {old_region} на {new_region}")
    if old_region == new_region:
        logger.info(f"Пользователь @{call.from_user.username} выбрал тот же регион: {new_region}")
        await call.answer("Этот регион уже выбран.", show_alert=True)
        return

    # Просто обновляем регион пользователя
    await update_user_region(user.tg_id, new_region)

    # Получаем обновлённого пользователя
    user = await get_user_by_tg_id(call.from_user.id)

    # Получаем активный баланс и бонус для нового региона
    balance, bonus, currency = get_active_balance(user)
    text = await get_profile_text(user, balance, bonus, currency)
    logger.info(f"Пользователь @{call.from_user.username} успешно сменил регион на {new_region}.")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=user_profile_keyboard())
    await state.clear()
    await call.answer("Регион изменён!")

@router.callback_query(F.data == "profile_cancel")
async def profile_cancel(call: CallbackQuery, state: FSMContext):
    """Отмена смены региона — возврат к профилю."""
    logger.info(f"Пользователь @{call.from_user.username} отменил смену региона")
    user = await get_user_by_tg_id(call.from_user.id)
    balance, bonus, currency = get_active_balance(user)
    text = await get_profile_text(user, balance, bonus, currency)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=user_profile_keyboard())
    await state.clear()
    await call.answer()