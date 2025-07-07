import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from app.keyboards.common.region import region_keyboard
from app.keyboards.user.main_menu import main_menu_keyboard
from app.keyboards.booster.booster_menu import booster_menu_keyboard
from app.keyboards.admin.admin_menu import admin_menu_keyboard
from app.database.crud import add_user, update_user_region, get_user_by_tg_id
from app.states.user_states import RegionStates

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await get_user_by_tg_id(message.from_user.id)
    if user:
        logger.info(f"@{message.from_user.username} (id={message.from_user.id}) повторно использовал /start")
        # Проверяем роль и показываем нужное меню
        if user.role == "admin":
            menu = admin_menu_keyboard()
        elif user.role == "booster":
            menu = booster_menu_keyboard()
        else:
            menu = main_menu_keyboard()
        await message.answer(
            "С возвращением! Вы уже зарегистрированы.",
            reply_markup=menu
        )
    else:
        await add_user(
            tg_id=message.from_user.id,
            username=message.from_user.username or ""
        )
        logger.info(f"@{message.from_user.username} (id={message.from_user.id}) зарегистрировался через /start")
        await message.answer(
            "Добро пожаловать!\nПожалуйста, выберите ваш регион:",
            reply_markup=region_keyboard()
        )
        await state.set_state(RegionStates.waiting_for_region)

@router.message(RegionStates.waiting_for_region)
async def region_chosen(message: Message, state: FSMContext):
    if message.text not in ["🇰🇬 КР", "🇰🇿 КЗ", "🇷🇺 РУ"]:
        await message.answer("Пожалуйста, выберите регион только с помощью кнопок ниже!")
        return
    await update_user_region(message.from_user.id, message.text)
    logger.info(f"@{message.from_user.username} (id={message.from_user.id}) выбрал регион: {message.text}")
    await message.answer(
        f"Ваш регион: {message.text}\nГлавное меню:",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()