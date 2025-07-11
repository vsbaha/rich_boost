from app.database.crud import get_payment_request_by_id, update_payment_request_status, get_user_by_id, update_user_balance_by_region, get_user_by_tg_id, get_all_payment_requests
from aiogram import Router, F
import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from app.utils.roles import admin_only
from app.utils.user import format_user_profile
from app.keyboards.admin.payments import admin_topup_action_keyboard, back_to_payment_keyboard

router = Router()
logger = logging.getLogger(__name__)

def admin_topup_action_keyboard(request_id, status, filter_status):
    buttons = []
    if status == "pending":
        buttons.append([
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"accept_payment:{request_id}:filter:{filter_status}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment:{request_id}:filter:{filter_status}")
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_filtered:{filter_status}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text == "💸 Все заявки на пополнение")
@admin_only
async def admin_all_topup_requests(message: Message):
    requests = await get_all_payment_requests()
    if not requests:
        await message.answer("Нет заявок на пополнение.")
        return

    # Клавиатура для фильтрации
    filter_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏳ В ожидании", callback_data="filter_topups:pending"),
                InlineKeyboardButton(text="✅ Принятые", callback_data="filter_topups:accepted"),
                InlineKeyboardButton(text="❌ Отклонённые", callback_data="filter_topups:rejected"),
            ]
        ]
    )

    text = "<b>Все заявки на пополнение:</b>\nВыберите заявку для подробностей:"
    await message.answer(text, parse_mode="HTML", reply_markup=filter_keyboard)

@router.callback_query(F.data.startswith("filter_topups:"))
@admin_only
async def filter_topup_requests(call: CallbackQuery):
    status = call.data.split(":")[1]
    requests = await get_all_payment_requests()
    filtered = [r for r in requests if r.status == status]
    if not filtered:
        await call.message.edit_text("Нет заявок с таким статусом.")
        await call.answer()
        return
    text = f"<b>Заявки со статусом: {status}</b>\nВыберите заявку для подробностей:"
    requests_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅' if req.status == 'accepted' else '❌' if req.status == 'rejected' else '⏳'} | "
                         f"{req.created_at.strftime('%d.%m.%Y %H:%M')} | "
                         f"{req.amount:.2f} | {req.region} | User ID: {req.user_id}",
                    callback_data=f"admin_topup_info:{req.id}:{status}"
                )
            ] for req in filtered
        ]
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=requests_keyboard)
    await call.answer()

@router.callback_query(F.data.startswith("admin_topup_info:"))
@admin_only
async def admin_topup_info(call: CallbackQuery):
    parts = call.data.split(":")
    request_id = int(parts[1])
    filter_status = parts[2] if len(parts) > 2 else "pending"
    payment_request = await get_payment_request_by_id(request_id)
    user = await get_user_by_id(payment_request.user_id)
    status = payment_request.status
    text = (
        f"<b>Заявка на пополнение</b>\n"
        f"ID: <code>{payment_request.id}</code>\n"
        f"Пользователь: @{user.username or '—'}\n"
        f"User ID: <code>{user.tg_id}</code>\n"
        f"Регион: {payment_request.region}\n"
        f"Сумма: {payment_request.amount:.2f}\n"
        f"Дата: {payment_request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Статус: {'✅ Принято' if status == 'accepted' else '❌ Отклонено' if status == 'rejected' else '⏳ В ожидании'}"
    )
    keyboard = admin_topup_action_keyboard(request_id, status, filter_status)
    await call.message.delete()
    if payment_request.receipt_file_id:
        await call.message.answer_photo(
            photo=payment_request.receipt_file_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data.startswith("accept_payment:"))
@admin_only
async def accept_payment(call: CallbackQuery):
    parts = call.data.split(":")
    request_id = int(parts[1])
    filter_status = parts[3] if len(parts) > 3 else "pending"
    payment_request = await get_payment_request_by_id(request_id)
    if payment_request.status != "pending":
        await call.answer("Заявка уже обработана!", show_alert=True)
        return
    user = await get_user_by_id(payment_request.user_id)
    await update_user_balance_by_region(user, payment_request.region, payment_request.amount)
    await update_payment_request_status(request_id, "accepted")
    await call.answer("Пополнение принято!")
    try:
        await call.bot.send_message(
            user.tg_id,
            f"✅ Ваша заявка на пополнение {payment_request.amount:.2f} {payment_request.region} принята! Баланс пополнен."
        )
    except Exception:
        pass
    # Показываем обновлённый список заявок с этим фильтром
    await show_filtered_requests(call, filter_status)

@router.callback_query(F.data.startswith("reject_payment:"))
@admin_only
async def reject_payment(call: CallbackQuery):
    parts = call.data.split(":")
    request_id = int(parts[1])
    filter_status = parts[3] if len(parts) > 3 else "pending"
    payment_request = await get_payment_request_by_id(request_id)
    if payment_request.status != "pending":
        await call.answer("Заявка уже обработана!", show_alert=True)
        return
    await update_payment_request_status(request_id, "rejected")
    user = await get_user_by_id(payment_request.user_id)
    await call.answer("Пополнение отклонено!")
    try:
        await call.bot.send_message(
            user.tg_id,
            f"❌ Ваша заявка на пополнение {payment_request.amount:.2f} {payment_request.region} отклонена."
        )
    except Exception:
        pass
    # Показываем обновлённый список заявок с этим фильтром
    await show_filtered_requests(call, filter_status)

@router.callback_query(F.data.startswith("back_to_filtered:"))
@admin_only
async def back_to_filtered(call: CallbackQuery):
    filter_status = call.data.split(":")[1]
    requests = await get_all_payment_requests()
    filtered = [r for r in requests if r.status == filter_status]
    if not filtered:
        await call.message.delete()
        await call.message.answer("Нет заявок с таким статусом.")
        await call.answer()
        return
    text = f"<b>Заявки со статусом: {filter_status}</b>\nВыберите заявку для подробностей:"
    requests_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅' if req.status == 'accepted' else '❌' if req.status == 'rejected' else '⏳'} | "
                         f"{req.created_at.strftime('%d.%m.%Y %H:%M')} | "
                         f"{req.amount:.2f} | {req.region} | User ID: {req.user_id}",
                    callback_data=f"admin_topup_info:{req.id}:{filter_status}"
                )
            ] for req in filtered
        ]
    )
    await call.message.delete()
    await call.message.answer(text, parse_mode="HTML", reply_markup=requests_keyboard)
    await call.answer()

async def show_filtered_requests(call: CallbackQuery, filter_status: str):
    requests = await get_all_payment_requests()
    filtered = [r for r in requests if r.status == filter_status]
    if not filtered:
        await call.message.delete()
        await call.message.answer("Нет заявок с таким статусом.")
        await call.answer()
        return
    text = f"<b>Заявки со статусом: {filter_status}</b>\nВыберите заявку для подробностей:"
    requests_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅' if req.status == 'accepted' else '❌' if req.status == 'rejected' else '⏳'} | "
                         f"{req.created_at.strftime('%d.%m.%Y %H:%M')} | "
                         f"{req.amount:.2f} | {req.region} | User ID: {req.user_id}",
                    callback_data=f"admin_topup_info:{req.id}:{filter_status}"
                )
            ] for req in filtered
        ]
    )
    await call.message.delete()
    await call.message.answer(text, parse_mode="HTML", reply_markup=requests_keyboard)
    await call.answer()