from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.database.crud import get_user_by_tg_id
from app.utils.referral import get_referral_link
from app.utils.referral import get_referrals_count
from app.database.models import BonusHistory
from app.database.db import AsyncSessionLocal
from sqlalchemy.future import select

router = Router()

@router.message(F.text == "🎁 Бонусы и рефералы")
async def bonuses_and_referrals(message: Message):
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Напишите /start для регистрации.")
        return

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

    # История бонусов (последние 5)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BonusHistory)
            .where(BonusHistory.user_id == user.id)
            .order_by(BonusHistory.created_at.desc())
            .limit(5)
        )
        history = result.scalars().all()

    history_text = ""
    if history:
        history_text = "\n\n<b>Последние бонусы:</b>"
        for h in history:
            comment = f" — <i>{h.comment}</i>" if h.comment else ""
            history_text += f"\n<b>+{h.amount:.2f} {currency}</b> ({h.source}){comment}"

    # Формируем подробную статистику по рефералам
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
        f"Приглашено друзей: <b>{len(referrals)}</b>\n"
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
            [InlineKeyboardButton(text="Поделиться ссылкой", switch_inline_query=share_text)]
        ]
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)