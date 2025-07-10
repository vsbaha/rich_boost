import logging
from aiogram import Router, F
from aiogram.types import Message
from app.database.crud import get_user_by_tg_id
from app.keyboards.user.balance import user_balance_keyboard
from app.utils.currency import get_currency, get_active_balance

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "💰 Баланс")
async def user_balance(message: Message):
    logger.info(f"Пользователь @{message.from_user.username} открыл экран Баланс")
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Напишите команду /start для регистрации.")
        return
    balance, bonus, currency = get_active_balance(user)
    text = (
        f"{user.region} Кошелёк\n\n"
        f"Ваш баланс: {balance:.2f} {currency}\n"
        f"Бонусный баланс: {bonus:.2f} {currency}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=user_balance_keyboard())