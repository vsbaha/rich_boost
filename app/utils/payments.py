from app.database.crud import get_admins
from app.keyboards.admin.payments import admin_payment_keyboard

async def notify_admins_about_payment(bot, payment_request, user):
    admins = await get_admins()
    for admin_id in admins:
        await bot.send_photo(
            chat_id=admin_id,
            photo=payment_request.receipt_file_id,
            caption=(
                f"💸 <b>Новая заявка на пополнение</b>\n"
                f"Пользователь: @{user.username or '—'}\n"
                f"ID: <code>{user.tg_id}</code>\n"
                f"Регион: {payment_request.region}\n"
                f"Сумма: {payment_request.amount:.2f}\n"
                f"Дата: {payment_request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            ),
            parse_mode="HTML",
            reply_markup=admin_payment_keyboard(payment_request.id, user.tg_id)
        )