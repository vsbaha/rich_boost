import logging
from aiogram import Router, F
from aiogram.types import Message
from app.keyboards.booster.booster_menu import booster_menu_keyboard
from app.utils.roles import booster_only

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "📦 заказы")
@booster_only
async def booster_orders(message: Message):
    await message.answer("Здесь будут ваши заказы как бустера.", reply_markup=booster_menu_keyboard())

@router.message(F.text == "💼 Бустерский счёт")
@booster_only
async def booster_balance(message: Message):
    await message.answer("Здесь будет информация о бустерском счёте.", reply_markup=booster_menu_keyboard())

@router.message(F.text == "📞 Связь с поддержкой")
@booster_only
async def booster_support(message: Message):
    await message.answer("Здесь будет связь с поддержкой.", reply_markup=booster_menu_keyboard())