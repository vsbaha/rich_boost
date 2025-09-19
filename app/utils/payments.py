from app.database.crud import get_admins
from app.keyboards.admin.payments import admin_payment_keyboard
from app.keyboards.admin.payout_keyboards import get_admin_payout_detail_keyboard

async def notify_admins_about_payment(bot, payment_request, user):
    admins = await get_admins()
    date_str = payment_request.created_at.strftime('%d.%m.%Y %H:%M')
    
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
                f"Дата: {date_str}\n"
            ),
            parse_mode="HTML",
            reply_markup=admin_payment_keyboard(payment_request.id, user.tg_id)
        )

async def notify_admins_about_payout_request(bot, payout_request, booster_account):
    """Уведомляет админов о новом запросе на выплату"""
    from app.utils.currency import get_currency_info
    
    admins = await get_admins()
    date_str = payout_request.created_at.strftime('%d.%m.%Y %H:%M')
    currency_info = get_currency_info(payout_request.currency)
    
    sent_count = 0
    for admin_id in admins:
        try:
            text = (
                f"💰 <b>Новый запрос на выплату</b>\n\n"
                f"👤 Бустер: @{booster_account.username or 'неизвестно'}\n"
                f"📋 Запрос: #{payout_request.id}\n"
                f"💳 Валюта: {currency_info['name']}\n"
                f"💰 Сумма: {payout_request.amount:.2f} {currency_info['symbol']}\n"
                f"📅 Дата: {date_str}\n"
            )
            
            # Добавляем реквизиты если есть
            if payout_request.payment_details:
                text += f"\n💳 <b>Реквизиты:</b>\n<code>{payout_request.payment_details}</code>\n"
            
            text += f"\n⏳ Статус: Ожидает обработки"
            
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML",
                reply_markup=get_admin_payout_detail_keyboard(payout_request.id, payout_request.status)
            )
            sent_count += 1
        except Exception as e:
            print(f"Ошибка отправки уведомления админу {admin_id}: {e}")
    
    print(f"Уведомление о запросе выплаты #{payout_request.id} отправлено {sent_count} из {len(admins)} админов")