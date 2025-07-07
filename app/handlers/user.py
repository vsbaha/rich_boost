import logging
from aiogram import Router, F
from aiogram.types import Message
from app.keyboards.user.main_menu import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "🎮 Создать заказ")
async def create_order(message: Message):
    await message.answer("Здесь будет создание заказа.", reply_markup=main_menu_keyboard())

@router.message(F.text == "📦 Мои заказы")
async def my_orders(message: Message):
    await message.answer("Здесь будет список ваших заказов.", reply_markup=main_menu_keyboard())

@router.message(F.text == "💰 Баланс")
async def balance(message: Message):
    await message.answer("Здесь будет информация о вашем балансе.", reply_markup=main_menu_keyboard())

@router.message(F.text == "👤 Профиль")
async def profile(message: Message):
    await message.answer("Здесь будет ваш профиль.", reply_markup=main_menu_keyboard())

@router.message(F.text == "🎟 Бонусы и рефералы")
async def bonuses(message: Message):
    await message.answer("Здесь будут бонусы и рефералы.", reply_markup=main_menu_keyboard())

@router.message(F.text == "📞 Связь с поддержкой")
async def support(message: Message):
    await message.answer("Здесь будет связь с поддержкой.", reply_markup=main_menu_keyboard())