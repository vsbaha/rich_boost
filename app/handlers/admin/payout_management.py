from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.utils.roles import admin_only
from app.states.admin_states import AdminStates
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "admin_payout_requests")
@admin_only
async def show_payout_requests(call: CallbackQuery):
    """Показать список запросов на выплату"""
    from app.database.crud import get_payout_requests
    from app.keyboards.admin.payout_keyboards import get_admin_payout_list_keyboard
    
    pending_requests = await get_payout_requests(status="pending", limit=10)
    
    if not pending_requests:
        from datetime import datetime
        current_time = datetime.now().strftime('%H:%M:%S')
        text = f"📋 <b>Запросы на выплату</b>\n\n"
        text += f"Нет ожидающих запросов на выплату.\n\n"
        text += f"🕒 Обновлено: {current_time}"
        
        try:
            await call.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_admin_payout_list_keyboard([])
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await call.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=get_admin_payout_list_keyboard([])
            )
        return
        
    from datetime import datetime
    current_time = datetime.now().strftime('%H:%M:%S')
    text = f"📋 <b>Запросы на выплату ({len(pending_requests)})</b>\n\n"
    
    for req in pending_requests:
        from app.utils.currency import get_currency_info
        from app.database.crud import get_booster_account_by_id
        
        # Получаем информацию о бустере
        booster_account = await get_booster_account_by_id(req.booster_account_id)
        currency_info = get_currency_info(req.currency)
        
        text += f"🔸 Запрос #{req.id}\n"
        if booster_account:
            text += f"👤 @{booster_account.username or 'неизвестно'}\n"
        text += f"💰 {req.amount:.2f} {currency_info['symbol']}\n"
        text += f"📅 {req.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    text += f"🕒 Обновлено: {current_time}"
    
    try:
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_admin_payout_list_keyboard(pending_requests)
        )
    except Exception:
        # Если не удалось отредактировать, отправляем новое сообщение
        await call.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_admin_payout_list_keyboard(pending_requests)
        )

@router.callback_query(F.data.startswith("admin_payout_view_"))
@admin_only
async def view_payout_request(call: CallbackQuery):
    """Подробный просмотр запроса на выплату"""
    from app.database.crud import get_payout_request_by_id, get_booster_account_by_id
    from app.keyboards.admin.payout_keyboards import get_admin_payout_detail_keyboard
    from app.utils.currency import get_currency_info
    
    request_id = int(call.data.split("_")[3])
    payout_request = await get_payout_request_by_id(request_id)
    
    if not payout_request:
        await call.answer("❌ Запрос не найден", show_alert=True)
        return
        
    # Получаем информацию о бустере
    booster_account = await get_booster_account_by_id(payout_request.booster_account_id)
    currency_info = get_currency_info(payout_request.currency)
    
    text = f"📄 <b>Запрос на выплату #{payout_request.id}</b>\n\n"
    
    if booster_account:
        text += f"👤 Бустер: @{booster_account.username or 'неизвестно'}\n"
        text += f"💰 Сумма: {payout_request.amount:.2f} {currency_info['symbol']}\n"
        text += f"💳 Валюта: {currency_info['name']}\n"
        text += f"📅 Дата создания: {payout_request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"⏳ Статус: {payout_request.status}\n\n"
        
        # Показываем реквизиты если есть
        if payout_request.payment_details:
            text += f"💳 <b>Реквизиты получателя:</b>\n<code>{payout_request.payment_details}</code>\n\n"
        
        # Показываем текущий баланс бустера
        current_balance = getattr(booster_account, f"balance_{payout_request.currency}")
        text += f"💼 Текущий баланс: {current_balance:.2f} {currency_info['symbol']}\n\n"
        
        if payout_request.admin_comment:
            text += f"💬 Комментарий админа: {payout_request.admin_comment}\n\n"
            
        text += "Выберите действие:"
    else:
        text += "❌ Ошибка: аккаунт бустера не найден"
    
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_payout_detail_keyboard(payout_request.id, payout_request.status)
    )

@router.callback_query(F.data.startswith("admin_approve_payout_"))
@admin_only
async def approve_payout_request(call: CallbackQuery, state: FSMContext):
    """Одобрить запрос на выплату - требует загрузки чека"""
    from app.states.admin_states import AdminStates
    
    request_id = int(call.data.split("_")[3])
    
    await call.message.edit_text(
        f"📄 <b>Подтверждение выплаты #{request_id}</b>\n\n"
        "Для завершения одобрения выплаты необходимо загрузить чек о переводе.\n\n"
        "📸 Отправьте фото чека:",
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.uploading_payout_receipt)
    await state.update_data(approve_request_id=request_id)

@router.message(AdminStates.uploading_payout_receipt)
@admin_only
async def process_receipt_upload(message: Message, state: FSMContext):
    """Обработка загруженного чека выплаты"""
    from app.database.crud import approve_payout_request, get_payout_request_by_id, get_user_by_id
    from aiogram import Bot
    from app.config import BOT_TOKEN
    
    # Проверяем что отправлено фото
    if not message.photo:
        await message.answer(
            "❌ Необходимо отправить фото чека. Попробуйте еще раз:"
        )
        return
    
    data = await state.get_data()
    request_id = data['approve_request_id']
    
    # Получаем file_id самого большого фото
    receipt_file_id = message.photo[-1].file_id
    
    # Одобряем запрос с чеком
    payout_request = await approve_payout_request(request_id, receipt_file_id)
    
    if payout_request:
        await message.answer(
            f"✅ <b>Запрос #{request_id} одобрен</b>\n\n"
            f"💰 Сумма: {payout_request.amount} {payout_request.currency.upper()}\n"
            f"📄 Чек сохранен и будет отправлен бустеру",
            parse_mode="HTML"
        )
        
        # Отправляем уведомление бустеру
        try:
            # Получаем данные бустера
            from app.database.crud import get_booster_account_by_id
            booster_account = await get_booster_account_by_id(payout_request.booster_account_id)
            
            if booster_account:
                user = await get_user_by_id(booster_account.user_id)
                if user:
                    bot = Bot(token=BOT_TOKEN)
                    
                    # Отправляем уведомление с чеком одним сообщением
                    notification_text = (
                        f"✅ <b>Выплата одобрена!</b>\n\n"
                        f"📋 Запрос: #{payout_request.id}\n"
                        f"💰 Сумма: {payout_request.amount} {payout_request.currency.upper()}\n"
                        f"📅 Дата: {payout_request.updated_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                        f"� Подтверждение перевода:"
                    )
                    
                    # Отправляем чек с текстом как подпись
                    await bot.send_photo(
                        user.tg_id,
                        receipt_file_id,
                        caption=notification_text,
                        parse_mode="HTML"
                    )
                    
                    await bot.session.close()
                    logger.info(f"Уведомление о выплате отправлено бустеру {user.tg_id}")
                    
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления бустеру: {e}")
        
        logger.info(f"Админ {message.from_user.id} одобрил запрос выплаты #{request_id} с чеком")
        await state.clear()
        
        # Показываем сообщение об успехе
        await message.answer(
            "✅ Запрос успешно обработан!\n"
            "Бустер получил уведомление с чеком."
        )
        
    else:
        await message.answer("❌ Ошибка при одобрении запроса")
        await state.clear()

@router.callback_query(F.data.startswith("admin_reject_payout_"))
@admin_only  
async def reject_payout_request(call: CallbackQuery, state: FSMContext):
    """Отклонить запрос на выплату"""
    from app.states.admin_states import AdminStates
    
    request_id = int(call.data.split("_")[3])
    
    await call.message.edit_text(
        f"❌ <b>Отклонение запроса #{request_id}</b>\n\n"
        "Введите причину отклонения:",
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.entering_reject_comment)
    await state.update_data(reject_request_id=request_id)

@router.message(AdminStates.entering_reject_comment)
@admin_only
async def process_reject_comment(message: Message, state: FSMContext):
    """Обработка комментария при отклонении"""
    from app.database.crud import update_payout_status
    
    data = await state.get_data()
    request_id = data['reject_request_id']
    comment = message.text
    
    # Обновляем статус в БД
    success = await update_payout_status(request_id, "rejected", message.from_user.id, comment)
    
    if success:
        await message.answer(
            f"✅ Запрос #{request_id} отклонен\n"
            f"Причина: {comment}"
        )
        
        # TODO: Отправить уведомление бустеру
        
        logger.info(f"Админ {message.from_user.id} отклонил запрос выплаты #{request_id}: {comment}")
    else:
        await message.answer("❌ Ошибка при отклонении запроса")
        
    await state.clear()

@router.callback_query(F.data == "admin_payout_history")
@admin_only
async def show_payout_history(call: CallbackQuery):
    """Показать историю выплат"""
    from app.database.crud import get_payout_requests
    from app.keyboards.admin.payout_keyboards import get_admin_payout_history_keyboard
    from datetime import datetime
    
    # Получаем последние обработанные запросы
    processed_requests = await get_payout_requests(status=None, limit=20)
    processed_requests = [req for req in processed_requests if req.status != "pending"]
    
    current_time = datetime.now().strftime('%H:%M:%S')
    
    if not processed_requests:
        text = f"📚 <b>История выплат</b>\n\n"
        text += f"История пуста.\n\n"
        text += f"🕒 Обновлено: {current_time}"
    else:
        text = f"📚 <b>История выплат ({len(processed_requests)})</b>\n\n"
        
        for req in processed_requests:
            from app.utils.currency import get_currency_info
            from app.database.crud import get_booster_account_by_id
            
            booster_account = await get_booster_account_by_id(req.booster_account_id)
            currency_info = get_currency_info(req.currency)
            
            status_emoji = {"approved": "✅", "rejected": "❌"}
            
            text += f"{status_emoji.get(req.status, '❓')} Запрос #{req.id}\n"
            if booster_account:
                text += f"👤 @{booster_account.username or 'неизвестно'}\n"
            text += f"💰 {req.amount:.2f} {currency_info['symbol']}\n"
            text += f"📅 {req.processed_at.strftime('%d.%m.%Y %H:%M') if req.processed_at else 'не обработан'}\n"
            
            if req.admin_comment:
                text += f"💬 {req.admin_comment}\n"
            text += "\n"
        
        text += f"🕒 Обновлено: {current_time}"

    try:
        await call.message.edit_text(
            text,
            parse_mode="HTML", 
            reply_markup=get_admin_payout_history_keyboard()
        )
    except Exception:
        # Если не удалось отредактировать, отправляем новое сообщение
        await call.message.answer(
            text,
            parse_mode="HTML", 
            reply_markup=get_admin_payout_history_keyboard()
        )

@router.callback_query(F.data == "admin_menu")
@admin_only
async def back_to_admin_menu(call: CallbackQuery):
    """Возврат в главное админ-меню"""
    from app.keyboards.admin.admin_menu import admin_menu_keyboard
    
    await call.message.answer(
        "👨‍💼 <b>Админ-панель</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard()
    )
    await call.answer()