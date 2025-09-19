from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.utils.roles import booster_only
from app.keyboards.booster.booster_menu import booster_menu_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("menu"))
@booster_only
async def booster_menu_command(message: Message):
    """Отображение главного меню бустера"""
    await message.answer(
        "🎮 <b>Меню бустера</b>\n\n"
        "Добро пожаловать в панель бустера!\n"
        "Выберите нужный раздел:",
        parse_mode="HTML",
        reply_markup=booster_menu_keyboard()
    )
    logger.info(f"Бустер @{message.from_user.username} открыл главное меню")
