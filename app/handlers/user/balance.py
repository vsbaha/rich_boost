import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.database.crud import get_user_by_tg_id, create_payment_request, get_payment_requests_by_user, get_payment_request_by_id
from app.keyboards.user.balance import user_balance_keyboard
from aiogram.fsm.context import FSMContext
from app.utils.currency import get_currency, get_active_balance
from app.states.user_states import TopUpStates
from app.utils.payments import notify_admins_about_payment
from app.config import MIN_TOPUP_KGS, MIN_TOPUP_KZT, MIN_TOPUP_RUB  # добавь в config.py минимальные суммы для каждого региона

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
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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

@router.callback_query(F.data == "user_topup")
async def start_topup(call: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg_id(call.from_user.id)
    min_amount = {
        "🇰🇬 КР": MIN_TOPUP_KGS,
        "🇰🇿 КЗ": MIN_TOPUP_KZT,
        "🇷🇺 РУ": MIN_TOPUP_RUB,
    }.get(user.region, 0)
    await call.message.edit_text(
        f"Введите сумму пополнения (минимум {min_amount}):",
        reply_markup=None
    )
    await state.set_state(TopUpStates.waiting_for_amount)
    await state.update_data(min_amount=min_amount, region=user.region)

@router.message(TopUpStates.waiting_for_amount)
async def topup_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    min_amount = data.get("min_amount", 0)
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введите корректную сумму!")
        return
    if amount < min_amount:
        await message.answer(f"Минимальная сумма пополнения: {min_amount}")
        return
    await state.update_data(amount=amount)
    # Реквизиты для региона
    region = data.get("region")
    requisites = {
        "🇰🇬 КР": "Kaspi/Элсом: +996 XXX XXX",
        "🇰🇿 КЗ": "Kaspi: +7 XXX XXX",
        "🇷🇺 РУ": "QIWI: +7 XXX XXX",
    }.get(region, "Реквизиты не указаны")
    await message.answer(
        f"Реквизиты для пополнения:\n{requisites}\n\n"
        f"Переведите {amount} и отправьте скриншот чека сюда."
    )
    await state.set_state(TopUpStates.waiting_for_receipt)

@router.message(TopUpStates.waiting_for_receipt)
async def topup_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount")
    region = data.get("region")
    if not message.photo:
        await message.answer("Пожалуйста, отправьте скриншот чека (фото).")
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
    
@router.callback_query(F.data == "user_history")
async def user_topup_history(call: CallbackQuery):
    user = await get_user_by_tg_id(call.from_user.id)
    all_requests = [req for req in await get_payment_requests_by_user(user.id) if req.region == user.region]
    if not all_requests:
        await call.message.answer("У вас нет заявок на пополнение в этом регионе.")
        await call.answer()
        return
    page = 1
    total_pages = (len(all_requests) + PAGE_SIZE - 1) // PAGE_SIZE
    requests = all_requests[(page-1)*PAGE_SIZE : page*PAGE_SIZE]
    text = "<b>История пополнений:</b>\nВыберите заявку для подробностей:"
    keyboard = get_history_keyboard(requests, page, total_pages)
    await call.message.delete()
    await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data.startswith("user_history_page:"))
async def user_topup_history_page(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    user = await get_user_by_tg_id(call.from_user.id)
    all_requests = [req for req in await get_payment_requests_by_user(user.id) if req.region == user.region]
    total_pages = (len(all_requests) + PAGE_SIZE - 1) // PAGE_SIZE
    requests = all_requests[(page-1)*PAGE_SIZE : page*PAGE_SIZE]
    text = "<b>История пополнений:</b>\nВыберите заявку для подробностей:"
    keyboard = get_history_keyboard(requests, page, total_pages)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data.startswith("user_topup_info:"))
async def user_topup_info(call: CallbackQuery):
    request_id = int(call.data.split(":")[1])
    payment_request = await get_payment_request_by_id(request_id)
    if not payment_request:
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
    if payment_request.receipt_file_id:
        await call.message.answer_photo(
            photo=payment_request.receipt_file_id,
            caption=text,
            parse_mode="HTML"
        )
    else:
        await call.message.answer(text, parse_mode="HTML")
    await call.answer()
