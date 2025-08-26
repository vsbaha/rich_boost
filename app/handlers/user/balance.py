import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.database.crud import get_user_by_tg_id, create_payment_request, get_payment_requests_by_user, get_payment_request_by_id
from app.keyboards.user.balance import user_balance_keyboard
from aiogram.fsm.context import FSMContext
from app.utils.currency import get_currency, get_active_balance
from app.states.user_states import TopUpStates
from app.utils.payments import notify_admins_about_payment
from app.config import REGION_CURRENCIES
from app.utils.settings import SettingsManager

router = Router()
logger = logging.getLogger(__name__)

PAGE_SIZE = 5

def get_history_keyboard(requests, page, total_pages):
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if req.status == 'accepted' else '❌' if req.status == 'rejected' else '⏳'} | "
                     f"{req.created_at.strftime('%d.%m.%Y %H:%M')} | "
                     f"{req.amount:.2f} {get_currency(req.region)}",
                callback_data=f"user_topup_info:{req.id}"
            )
            
        ] for req in requests
    ]
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"user_history_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"user_history_page:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton(text="⬅️ В меню баланса", callback_data="user_balance_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text == "💰 Баланс")
async def user_balance(message: Message):
    logger.info(f"Пользователь @{message.from_user.username or 'без username'} открыл экран Баланс")
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        logger.info(f"Пользователь @{message.from_user.username or 'без username'} не найден")
        await message.answer("Профиль не найден. Напишите команду /start для регистрации.")
        return
    balance, bonus, currency = get_active_balance(user)
    text = (
        f"{user.region} Кошелёк\n\n"
        f"Ваш баланс: {balance:.2f} {currency}\n"
        f"Бонусный баланс: {bonus:.2f} {currency}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=user_balance_keyboard())
    logger.info(f"Пользователь @{message.from_user.username or 'без username'} увидел свой баланс")

@router.callback_query(F.data == "user_topup")
async def start_topup(call: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} начал пополнение баланса")
    user = await get_user_by_tg_id(call.from_user.id)
    
    # Получаем минимальные суммы из настроек по региону
    if user.region == "🇰🇬 КР":
        min_amount = await SettingsManager.get_setting("MIN_TOPUP_KGS")
    elif user.region == "🇰🇿 КЗ":
        min_amount = await SettingsManager.get_setting("MIN_TOPUP_KZT")
    else:  # "🇷🇺 РУ"
        min_amount = await SettingsManager.get_setting("MIN_TOPUP_RUB")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="user_balance_back")]
        ]
    )
    await call.message.edit_text(
        f"Введите сумму пополнения (минимум {min_amount}):",
        reply_markup=keyboard
    )
    await state.set_state(TopUpStates.waiting_for_amount)
    await state.update_data(min_amount=min_amount, region=user.region)
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} выбрал регион {user.region} для пополнения")

@router.message(TopUpStates.waiting_for_amount)
async def topup_amount(message: Message, state: FSMContext):
    logger.info(f"Пользователь @{message.from_user.username or 'без username'} вводит сумму пополнения")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="user_balance_back")]
        ]
    )
    data = await state.get_data()
    min_amount = data.get("min_amount", 0)
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        logger.info(f"Пользователь @{message.from_user.username or 'без username'} ввёл некорректную сумму")
        await message.answer("Введите корректную сумму!", reply_markup=keyboard)
        return
    if amount < min_amount:
        logger.info(f"Пользователь @{message.from_user.username or 'без username'} ввёл сумму меньше минимальной")
        await message.answer(f"Минимальная сумма пополнения: {min_amount}", reply_markup=keyboard)
        return
    await state.update_data(amount=amount)
    region = data.get("region")
    requisites = {
        "🇰🇬 КР": "Kaspi/Элсом: +996 XXX XXX",
        "🇰🇿 КЗ": "Kaspi: +7 XXX XXX",
        "🇷🇺 РУ": "QIWI: +7 XXX XXX",
    }.get(region, "Реквизиты не указаны")
    await message.answer(
        f"Реквизиты для пополнения:\n{requisites}\n\n"
        f"Переведите {amount} и отправьте скриншот чека сюда.", reply_markup=keyboard
    )
    await state.set_state(TopUpStates.waiting_for_receipt)
    logger.info(f"Пользователь @{message.from_user.username or 'без username'} получил реквизиты для пополнения")

@router.message(TopUpStates.waiting_for_receipt)
async def topup_receipt(message: Message, state: FSMContext):
    logger.info(f"Пользователь @{message.from_user.username or 'без username'} отправляет чек")
    data = await state.get_data()
    amount = data.get("amount")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="user_balance_back")]
        ]
    )
    if not message.photo:
        logger.info(f"Пользователь @{message.from_user.username or 'без username'} не отправил фото чека")
        await message.answer("Пожалуйста, отправьте скриншот чека (фото).", reply_markup=keyboard)
        return
    file_id = message.photo[-1].file_id
    user = await get_user_by_tg_id(message.from_user.id)
    payment_request = await create_payment_request(
        user_id=user.id,
        region=user.region,
        amount=amount,
        receipt_file_id=file_id
    )
    bot = message.bot
    await notify_admins_about_payment(bot, payment_request, user)
    await message.answer("Ваша заявка на пополнение отправлена админу. Ожидайте подтверждения.")
    await state.clear()
    logger.info(f"Пользователь @{message.from_user.username or 'без username'} отправил заявку на пополнение")

@router.callback_query(F.data == "user_history")
async def user_topup_history(call: CallbackQuery):
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} открыл историю пополнений")
    user = await get_user_by_tg_id(call.from_user.id)
    all_requests = [req for req in await get_payment_requests_by_user(user.id) if req.region == user.region]
    if not all_requests:
        logger.info(f"Пользователь @{call.from_user.username or 'без username'} не имеет заявок на пополнение")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="user_balance_back")]
            ]
        )
        await call.message.edit_text("У вас нет заявок на пополнение в этом регионе.", reply_markup=keyboard)
        await call.answer()
        return
    page = 1
    total_pages = (len(all_requests) + PAGE_SIZE - 1) // PAGE_SIZE
    requests = all_requests[(page-1)*PAGE_SIZE : page*PAGE_SIZE]
    text = "<b>История пополнений:</b>\nВыберите заявку для подробностей:"
    keyboard = get_history_keyboard(requests, page, total_pages)
    await call.message.delete()
    await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} просмотрел страницу истории пополнений")
    await call.answer()

@router.callback_query(F.data.startswith("user_history_page:"))
async def user_topup_history_page(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} переключил страницу истории: {page}")
    user = await get_user_by_tg_id(call.from_user.id)
    all_requests = [req for req in await get_payment_requests_by_user(user.id) if req.region == user.region]
    total_pages = (len(all_requests) + PAGE_SIZE - 1) // PAGE_SIZE
    requests = all_requests[(page-1)*PAGE_SIZE : page*PAGE_SIZE]
    text = "<b>История пополнений:</b>\nВыберите заявку для подробностей:"
    keyboard = get_history_keyboard(requests, page, total_pages)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} просмотрел страницу истории пополнений: {page}")
    await call.answer()

@router.callback_query(F.data.startswith("user_topup_info:"))
async def user_topup_info(call: CallbackQuery):
    request_id = int(call.data.split(":")[1])
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} просматривает заявку на пополнение ID {request_id}")
    payment_request = await get_payment_request_by_id(request_id)
    if not payment_request:
        logger.info(f"Пользователь @{call.from_user.username or 'без username'}: заявка ID {request_id} не найдена")
        await call.answer("Заявка не найдена.", show_alert=True)
        return
    status = "✅ Принято" if payment_request.status == "accepted" else "❌ Отклонено" if payment_request.status == "rejected" else "⏳ В ожидании"
    currency = get_currency(payment_request.region)
    text = (
        f"<b>Заявка на пополнение</b>\n"
        f"ID: <code>{payment_request.id}</code>\n"
        f"Сумма: {payment_request.amount:.2f} {currency}\n"
        f"Регион: {payment_request.region}\n"
        f"Дата: {payment_request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Статус: {status}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="user_history_back")]
        ]
    )
    if payment_request.receipt_file_id:
        await call.message.delete()
        await call.message.answer_photo(
            photo=payment_request.receipt_file_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logger.info(f"Пользователь @{call.from_user.username or 'без username'} просмотрел заявку ID {request_id} (с фото)")
    else:
        await call.message.delete()
        await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        logger.info(f"Пользователь @{call.from_user.username or 'без username'} просмотрел заявку ID {request_id} (без фото)")
    await call.answer()

@router.callback_query(F.data == "user_history_back")
async def user_history_back(call: CallbackQuery):
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} вернулся к истории пополнений")
    user = await get_user_by_tg_id(call.from_user.id)
    all_requests = [req for req in await get_payment_requests_by_user(user.id) if req.region == user.region]
    if not all_requests:
        logger.info(f"Пользователь @{call.from_user.username or 'без username'} не имеет заявок на пополнение")
        await call.message.edit_text("У вас нет заявок на пополнение в этом регионе.")
        await call.answer()
        return
    page = 1
    total_pages = (len(all_requests) + PAGE_SIZE - 1) // PAGE_SIZE
    requests = all_requests[(page-1)*PAGE_SIZE : page*PAGE_SIZE]
    text = "<b>История пополнений:</b>\nВыберите заявку для подробностей:"
    keyboard = get_history_keyboard(requests, page, total_pages)
    await call.message.delete()
    await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} просмотрел страницу истории пополнений")
    await call.answer()

@router.callback_query(F.data == "user_balance_back")
async def user_balance_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    logger.info(f"Пользователь @{call.from_user.username or 'без username'} вернулся в меню баланса")
    user = await get_user_by_tg_id(call.from_user.id)
    balance, bonus, currency = get_active_balance(user)
    text = (
        f"{user.region} Кошелёк\n\n"
        f"Ваш баланс: {balance:.2f} {currency}\n"
        f"Бонусный баланс: {bonus:.2f} {currency}"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=user_balance_keyboard())
    await call.answer()
