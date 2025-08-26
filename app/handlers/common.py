import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from app.keyboards.common.region import region_keyboard
from app.keyboards.user.main_menu import main_menu_keyboard
from app.keyboards.booster.booster_menu import booster_menu_keyboard
from app.keyboards.admin.admin_menu import admin_menu_keyboard
from app.database.crud import (
    add_user,
    update_user_region,
    get_user_by_tg_id,
    get_user_by_id,
)
from app.states.user_states import RegionStates
from app.config import BOT_TOKEN

router = Router()
logger = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    referrer_id = None
    if len(parts) > 1 and parts[1].startswith("ref"):
        try:
            referrer_id = int(parts[1].replace("ref", ""))
        except ValueError:
            referrer_id = None

    user = await get_user_by_tg_id(message.from_user.id)
    if user:
        logger.info(
            f"@{message.from_user.username} (id={message.from_user.id}) повторно использовал /start"
        )
        # Проверяем роль и показываем нужное меню
        if user.role == "admin":
            menu = admin_menu_keyboard()
        elif user.role == "booster":
            menu = booster_menu_keyboard()
        else:
            menu = main_menu_keyboard()
        await message.answer(
            "С возвращением! Вы уже зарегистрированы.", reply_markup=menu
        )
    else:
        await add_user(
            tg_id=message.from_user.id,
            username=message.from_user.username or "",
            referrer_id=referrer_id,
        )
        logger.info(
            f"@{message.from_user.username} (id={message.from_user.id}) зарегистрировался через /start"
        )
        await message.answer(
            "Добро пожаловать!\nПожалуйста, выберите ваш регион:",
            reply_markup=region_keyboard(),
        )
        await state.set_state(RegionStates.waiting_for_region)

        if referrer_id:
            referrer = await get_user_by_id(referrer_id)  # функция, возвращающая User по id
            if referrer:
                try:
                    user_link = f"@{message.from_user.username}" if message.from_user.username else f"<a href='tg://user?id={message.from_user.id}'>Новый пользователь</a>"
                    await bot.send_message(
                        referrer.tg_id,
                        f"По вашей ссылке зарегистрировался новый пользователь: {user_link}",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass


@router.message(RegionStates.waiting_for_region)
async def choose_region(message: Message, state: FSMContext):
    region = message.text.strip()
    valid_regions = ["🇰🇬 КР", "🇰🇿 КЗ", "🇷🇺 РУ"]
    if region not in valid_regions:
        await message.answer(
            "Пожалуйста, выберите регион с помощью кнопок ниже.",
            reply_markup=region_keyboard(),
        )
        return
    await update_user_region(message.from_user.id, region)
    logger.info(
        f"@{message.from_user.username} (id={message.from_user.id}) выбрал регион: {region}"
    )
    await state.clear()
    await message.answer(
        f"Регион выбран: {region}\nТеперь вы можете пользоваться ботом!",
        reply_markup=main_menu_keyboard(),
    )


@router.message()
async def unknown_message(message: Message):
    user = await get_user_by_tg_id(message.from_user.id)
    if user:
        if user.role == "admin":
            menu = admin_menu_keyboard()
        elif user.role == "booster":
            menu = booster_menu_keyboard()
        else:
            menu = main_menu_keyboard()
    else:
        menu = main_menu_keyboard()
    await message.answer(
        "Я не понял ваш запрос. Пожалуйста, используйте кнопки меню или команды.",
        reply_markup=menu,
    )


@router.callback_query(F.data.startswith("set_region:"))
async def set_user_region(call: CallbackQuery, state: FSMContext):
    region = call.data.split(":")[1]
    await update_user_region(call.from_user.id, region)
    logger.info(
        f"@{call.from_user.username} (id={call.from_user.id}) сменил регион на: {region}"
    )
    await state.clear()
    await call.message.edit_text(
        f"Регион выбран: {region}\nТеперь вы можете пользоваться ботом!",
        reply_markup=main_menu_keyboard(),
    )