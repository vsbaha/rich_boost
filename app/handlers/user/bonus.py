from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.database.crud import check_and_activate_promo, get_user_by_tg_id, delete_expired_promocodes
from app.utils.referral import get_referral_link, get_referrals_count
from app.database.models import BonusHistory
from app.database.db import AsyncSessionLocal
from sqlalchemy.future import select
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from app.states.user_states import PromoStates
import logging

router = Router()

BONUS_PAGE_SIZE = 10

logger = logging.getLogger(__name__)

async def get_bonuses_text_and_keyboard(user):
    referrals = await get_referrals_count(user.id)
    ref_link = get_referral_link(user)

    # Суммируем бонусы
    if user.region == "🇰🇬 КР":
        bonus = user.bonus_kg
        currency = "сом"
    elif user.region == "🇰🇿 КЗ":
        bonus = user.bonus_kz
        currency = "тенге"
    elif user.region == "🇷🇺 РУ":
        bonus = user.bonus_ru
        currency = "руб."
    else:
        bonus = 0
        currency = ""

    # История бонусов (последние 5) и статистика
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BonusHistory)
            .where(BonusHistory.user_id == user.id)
            .order_by(BonusHistory.created_at.desc())
            .limit(5)
        )
        history = result.scalars().all()

        result_all = await session.execute(
            select(BonusHistory)
            .where(BonusHistory.user_id == user.id, BonusHistory.source == "Реферал")
        )
        all_ref_bonuses = result_all.scalars().all()
        total_ref_bonus = sum(b.amount for b in all_ref_bonuses)
        referrals_with_bonus = [b.comment for b in all_ref_bonuses if b.comment]
        referrals_with_topup = len(referrals_with_bonus)

    # История бонусов (оформление)
    history_text = ""
    if history:
        history_text = "\n\n<b>Последние бонусы:</b>"
        for h in history:
            comment = f" — <i>{h.comment}</i>" if h.comment else ""
            history_text += f"\n<b>+{h.amount:.2f} {currency}</b> ({h.source}){comment}"

    # Подробная статистика по рефералам
    if referrals:
        referrals_text = "\n\n<b>Ваши приглашённые:</b>"
        for r in referrals:
            reg_date = r.created_at.strftime('%d.%m.%Y')
            username = f"@{r.username}" if r.username else f"<code>{r.tg_id}</code>"
            referrals_text += f"\n• {username} ({reg_date})"
    else:
        referrals_text = "\n\n<b>Ваши приглашённые:</b>\n—"

    text = (
        f"<b>🎁 Бонусы и рефералы</b>\n"
        f"Бонусный баланс: <b>{bonus:.2f} {currency}</b>\n"
        f"Всего заработано бонусов за рефералов: <b>{total_ref_bonus:.2f} {currency}</b>\n"
        f"Рефералов с пополнением: <b>{referrals_with_topup}</b>\n"
        f"Пригласито друзей: <b>{len(referrals)}</b>\n"
        f"Ваша реферальная ссылка:\n<code>{ref_link}</code>"
        f"\n\n👥 <i>Пригласите друга по ссылке и получите бонус за его первое пополнение!</i>"
        f"{referrals_text}"
        f"{history_text}"
    )

    share_text = (
        "🎁 Получи бонус за регистрацию!\n"
        "Регистрируйся в Rich Boost и получай подарки!\n"
        f"👉 {ref_link}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пригласить друга", switch_inline_query=share_text)],
            [InlineKeyboardButton(text="История бонусов", callback_data="bonus_history:all:1")],
            [InlineKeyboardButton(text="Активировать промокод", callback_data="activate_promo")]
        ]
    )
    return text, keyboard

@router.message(F.text == "🎁 Бонусы и рефералы")
async def bonuses_and_referrals(message: Message):
    logger.info(f"Пользователь @{message.from_user.username} открыл меню бонусов и рефералов")
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Напишите /start для регистрации.")
        return
    text, keyboard = await get_bonuses_text_and_keyboard(user)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data == "show_bonus_history")
async def show_bonus_history(call: CallbackQuery):
    logger.info(f"Пользователь @{call.from_user.username} открыл всю историю бонусов")
    user = await get_user_by_tg_id(call.from_user.id)
    if not user:
        await call.message.answer("Профиль не найден. Напишите /start для регистрации.")
        return
    try:
        await call.message.delete()
    except Exception:
        pass

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BonusHistory)
            .where(BonusHistory.user_id == user.id)
            .order_by(BonusHistory.created_at.desc())
            .limit(30)
        )
        history = result.scalars().all()

    if not history:
        await call.message.answer("У вас пока нет бонусов.")
        return

    text = "<b>Вся история бонусов:</b>"
    for h in history:
        comment = f" — <i>{h.comment}</i>" if h.comment else ""
        text += f"\n<b>+{h.amount:.2f}</b> ({h.source}){comment}"

    # Кнопка "Назад"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_bonuses")]
        ]
    )

    await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data == "back_to_bonuses")
async def back_to_bonuses(call: CallbackQuery):
    logger.info(f"Пользователь @{call.from_user.username} вернулся в меню бонусов")
    try:
        await call.message.delete()
    except Exception:
        pass

    user = await get_user_by_tg_id(call.from_user.id)
    if not user:
        await call.message.answer("Профиль не найден. Напишите /start для регистрации.")
        return
    text, keyboard = await get_bonuses_text_and_keyboard(user)
    await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

def filter_keyboard(current_filter, page, total_count):
    filters = [
        InlineKeyboardButton(
            text=("✅ Все" if current_filter == "all" else "Все"),
            callback_data="bonus_history:all:1"
        ),
        InlineKeyboardButton(
            text=("✅ Рефералы" if current_filter == "ref" else "Рефералы"),
            callback_data="bonus_history:ref:1"
        ),
        InlineKeyboardButton(
            text=("✅ Промокоды" if current_filter == "promo" else "Промокоды"),
            callback_data="bonus_history:promo:1"
        ),
    ]
    nav = []
    max_page = max(1, (total_count + BONUS_PAGE_SIZE - 1) // BONUS_PAGE_SIZE)
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bonus_history:{current_filter}:{page-1}"))
    if page < max_page:
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"bonus_history:{current_filter}:{page+1}"))
    menu = [InlineKeyboardButton(text="🏠 В меню бонусов", callback_data="back_to_bonuses")]
    return InlineKeyboardMarkup(inline_keyboard=[filters, nav, menu])

@router.callback_query(F.data.startswith("bonus_history"))
async def bonus_history_paginated(call: CallbackQuery):
    logger.info(f"Пользователь @{call.from_user.username} листает историю бонусов: фильтр {call.data}")
    user = await get_user_by_tg_id(call.from_user.id)
    if not user:
        await call.message.answer("Профиль не найден. Напишите /start для регистрации.")
        return

    # Парсим фильтр и страницу
    parts = call.data.split(":")
    filter_type = parts[1] if len(parts) > 1 else "all"
    page = int(parts[2]) if len(parts) > 2 else 1

    filters = [BonusHistory.user_id == user.id]
    if filter_type == "ref":
        filters.append(BonusHistory.source == "Реферал")
    elif filter_type == "promo":
        filters.append(BonusHistory.source == "Промокод")

    async with AsyncSessionLocal() as session:
        total_query = await session.execute(
            select(BonusHistory).where(*filters)
        )
        total = total_query.scalars().all()
        total_count = len(total)

        result = await session.execute(
            select(BonusHistory)
            .where(*filters)
            .order_by(BonusHistory.created_at.desc())
            .offset((page - 1) * BONUS_PAGE_SIZE)
            .limit(BONUS_PAGE_SIZE)
        )
        history = result.scalars().all()

    if not history:
        await call.message.edit_text("Нет бонусов по выбранному фильтру.", reply_markup=filter_keyboard(filter_type, page, total_count))
        return

    text = "<b>История бонусов:</b>"
    for h in history:
        # Красивое оформление типа бонуса
        if h.source == "Реферал":
            source = "👤 <b>Реферал</b>"
        elif h.source == "Промокод":
            source = "🎟️ <b>Промокод</b>"
        else:
            source = f"🏷️ <b>{h.source}</b>"

        comment = f" — <i>{h.comment}</i>" if h.comment else ""
        text += f"\n<b>+{h.amount:.2f}</b> {source}{comment}"

    keyboard = filter_keyboard(filter_type, page, total_count)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await call.answer("Вы уже на этой странице!", show_alert=True)
        else:
            raise

@router.callback_query(F.data == "activate_promo")
async def activate_promo_start(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь @{call.from_user.username} начал активацию промокода")
    await call.message.answer("Введите промокод для активации:")
    await state.set_state(PromoStates.waiting_for_promo_code)

@router.message(PromoStates.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    logger.info(f"Пользователь @{message.from_user.username} пытается активировать промокод: {message.text.strip()}")
    # Удаляем истёкшие промокоды перед активацией
    await delete_expired_promocodes()

    code = message.text.strip().upper()
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Напишите /start для регистрации.")
        await state.clear()
        return

    ok, msg = await check_and_activate_promo(user.id, code)
    logger.info(f"Пользователь @{message.from_user.username} результат активации промокода: {msg}")
    await message.answer(msg)
    await state.clear()