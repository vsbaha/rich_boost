from aiogram import Router, F
from aiogram.types import Message
from app.config import ADMIN_USERNAME
router = Router()


@router.message(F.text == "📞 Поддержка")
async def booster_support_contact(message: Message):
    await message.answer(
        f"Для связи с поддержкой напишите админу: @{ADMIN_USERNAME}"
    )