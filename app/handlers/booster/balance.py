




from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.utils.roles import booster_only
from app.keyboards.booster.balance_menu import (
    booster_balance_keyboard, 
    booster_convert_menu_keyboard, 
    conversion_confirm_keyboard
)
from app.keyboards.booster.payout_keyboards import get_back_to_balance_keyboard
from app.utils.currency import get_currency_info
from app.states.booster_states import BoosterStates
from app.database import crud
import logging

router = Router()
logger = logging.getLogger(__name__)

# === HELPER FUNCTIONS ===

async def get_booster_data(user_id: int):
    """Получает данные бустера и пользователя"""
    from app.database.crud import get_booster_account, get_user_by_tg_id
    
    booster_account = await get_booster_account(user_id)
    user = await get_user_by_tg_id(user_id)
    
    return booster_account, user

def format_balance_text(booster_account) -> str:
    """Форматирует текст баланса бустера"""
    text = "💰 <b>Ваш бустерский баланс</b>\n\n"
    text += f"💵 <b>{booster_account.balance_usd:.2f} USD</b> (основной баланс)\n"
    
    # Добавляем локальные валюты если есть
    if booster_account.balance_kg > 0:
        text += f"🇰🇬 <b>{booster_account.balance_kg:.2f} сом</b>\n"
    if booster_account.balance_kz > 0:
        text += f"🇰🇿 <b>{booster_account.balance_kz:.2f} тенге</b>\n"  
    if booster_account.balance_ru > 0:
        text += f"🇷🇺 <b>{booster_account.balance_ru:.2f} руб.</b>\n"
    
    text += "\n<i>💡 Все новые выплаты начисляются только в USD. Для вывода сконвертируйте нужную сумму в локальную валюту.</i>"
    return text

def get_local_currency_info():
    """Возвращает информацию о валютах"""
    return {
        "region_names": {
            "kg": "сомы 🇰🇬",
            "kz": "тенге 🇰🇿",
            "ru": "рубли 🇷🇺"
        },
        "currency_codes": {
            "kg": "сом",
            "kz": "тенге", 
            "ru": "руб."
        }
    }

async def show_balance_menu(message_or_call, booster_account, edit=False):
    """Универсальная функция для показа меню баланса"""
    text = format_balance_text(booster_account)
    
    if edit and hasattr(message_or_call, 'message'):
        try:
            # Пытаемся редактировать текстовое сообщение
            await message_or_call.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=booster_balance_keyboard()
            )
            # Отвечаем на callback после успешного редактирования
            if hasattr(message_or_call, 'answer'):
                await message_or_call.answer()
        except Exception as e:
            # Если не получается (например, сообщение с фото), удаляем и отправляем новое
            if "no text in the message to edit" in str(e).lower() or "message to edit not found" in str(e).lower():
                try:
                    await message_or_call.message.delete()
                except:
                    pass  # Игнорируем ошибки удаления
                
                await message_or_call.message.answer(
                    text,
                    parse_mode="HTML",
                    reply_markup=booster_balance_keyboard()
                )
            else:
                # Для других ошибок просто отправляем новое сообщение
                await message_or_call.message.answer(
                    text,
                    parse_mode="HTML",
                    reply_markup=booster_balance_keyboard()
                )
            # Отвечаем на callback после восстановления
            if hasattr(message_or_call, 'answer'):
                await message_or_call.answer()
    else:
        await message_or_call.answer(
            text,
            parse_mode="HTML",
            reply_markup=booster_balance_keyboard()
        )

# === MAIN HANDLERS ===

@router.message(F.text == "💰 Мой баланс")
@booster_only
async def show_booster_balance(message: Message):
    """Показать баланс бустера с возможностью конвертации"""
    booster_account, user = await get_booster_data(message.from_user.id)
    
    if not booster_account:
        await message.answer("❌ Аккаунт бустера не найден!")
        return
    
    await show_balance_menu(message, booster_account)
    logger.info(f"Бустер @{message.from_user.username} проверил баланс: USD {booster_account.balance_usd}")

# === EXCHANGE RATES HANDLERS ===

@router.callback_query(F.data.in_(["booster_show_rates", "booster_refresh_rates"]))
@booster_only
async def handle_exchange_rates(call: CallbackQuery):
    """Показать или обновить курсы валют"""
    from app.utils.currency_converter import get_current_rates, converter
    from app.keyboards.booster.payout_keyboards import get_back_to_balance_keyboard
    
    is_refresh = call.data == "booster_refresh_rates"
    
    try:
        if is_refresh:
            converter.cache = {}  # Очищаем кэш для принудительного обновления
            
        rates = await get_current_rates()
        
        title = "🔄 <b>Курсы обновлены!</b>" if is_refresh else "📊 <b>Текущие курсы валют</b>"
        text = f"{title}\n\n"
        text += f"🇰🇬→🇰🇿 1 сом = {rates.get('KGS_to_KZT', 0):.3f} тенге\n"
        text += f"🇰🇬→🇷🇺 1 сом = {rates.get('KGS_to_RUB', 0):.3f} руб.\n"
        text += f"🇰🇿→🇰🇬 1 тенге = {rates.get('KZT_to_KGS', 0):.3f} сом\n"
        text += f"🇰🇿→🇷🇺 1 тенге = {rates.get('KZT_to_RUB', 0):.3f} руб.\n"
        text += f"🇷🇺→🇰🇬 1 руб. = {rates.get('RUB_to_KGS', 0):.3f} сом\n"
        text += f"🇷🇺→🇰🇿 1 руб. = {rates.get('RUB_to_KZT', 0):.3f} тенге\n\n"
        text += "💡 <i>Данные обновляются каждый час</i>" if not is_refresh else "💡 <i>Курсы успешно обновлены</i>"
        
        # Добавляем клавиатуру с кнопкой "Назад"
        keyboard = get_back_to_balance_keyboard()
        
        success_msg = "✅ Курсы обновлены!" if is_refresh else None
        if success_msg:
            await call.answer(success_msg)
        else:
            await call.answer()  # Отвечаем на callback
            
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        error_msg = f"Ошибка {'обновления' if is_refresh else 'получения'} курсов"
        logger.error(f"{error_msg}: {e}")
        await call.answer(f"❌ {error_msg}", show_alert=True)

# === PAYOUT HANDLERS ===

@router.callback_query(F.data == "booster_request_payout")
@booster_only
async def booster_request_payout(call: CallbackQuery, state: FSMContext):
    """Начало процесса запроса выплаты"""
    from app.keyboards.booster.payout_keyboards import get_payout_currency_keyboard
    
    booster_account, user = await get_booster_data(call.from_user.id)
    
    if not booster_account or not user:
        await call.answer("❌ Ошибка получения данных", show_alert=True)
        return

    # Проверяем доступные средства для выплаты
    available_balances = []
    if booster_account.balance_kg > 0:
        available_balances.append(f"🇰🇬 {booster_account.balance_kg:.2f} сом")
    if booster_account.balance_kz > 0:
        available_balances.append(f"🇰🇿 {booster_account.balance_kz:.2f} тенге")
    if booster_account.balance_ru > 0:
        available_balances.append(f"🇷🇺 {booster_account.balance_ru:.2f} руб.")

    if not available_balances:
        await call.answer(
            "❌ Для запроса выплаты сначала сконвертируйте USD в нужную валюту через меню.",
            show_alert=True
        )
        return

    text = "💸 <b>Запрос выплаты</b>\n\n"
    text += "Доступно к выводу:\n" + "\n".join(available_balances) + "\n\n"
    text += "Выберите валюту для вывода:"

    await call.message.edit_text(
        text, 
        parse_mode="HTML",
        reply_markup=get_payout_currency_keyboard()
    )
    await state.set_state(BoosterStates.selecting_payout_currency)

@router.callback_query(F.data.startswith("payout_currency_"))
@booster_only
async def select_payout_currency(call: CallbackQuery, state: FSMContext):
    """Выбор валюты для выплаты"""
    currency = call.data.split("_")[2]  # kg, kz, ru
    
    booster_account, user = await get_booster_data(call.from_user.id)
    if not booster_account:
        await call.answer("❌ Ошибка получения данных", show_alert=True)
        return
    
    # Проверяем наличие средств в выбранной валюте
    if currency == "kg" and booster_account.balance_kg <= 0:
        await call.answer("❌ Недостаточно средств в сомах", show_alert=True)
        return
    elif currency == "kz" and booster_account.balance_kz <= 0:
        await call.answer("❌ Недостаточно средств в тенге", show_alert=True)
        return
    elif currency == "ru" and booster_account.balance_ru <= 0:
        await call.answer("❌ Недостаточно средств в рублях", show_alert=True)
        return
    
    # Получаем информацию о валюте
    currency_info = get_currency_info(currency)
    balance = getattr(booster_account, f"balance_{currency}")
    
    text = f"💰 <b>Запрос выплаты в {currency_info['name']}</b>\n\n"
    text += f"Доступный баланс: {balance:.2f} {currency_info['symbol']}\n\n"
    text += "Введите сумму для вывода:"
    
    await call.message.edit_text(text, parse_mode="HTML")
    await state.set_state(BoosterStates.entering_payout_amount)
    await state.update_data(payout_currency=currency, max_amount=balance)

@router.message(BoosterStates.entering_payout_amount)
@booster_only
async def process_payout_amount(message: Message, state: FSMContext):
    """Обработка введенной суммы выплаты"""
    from app.keyboards.booster.payout_keyboards import get_back_to_balance_keyboard
    
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("Сумма должна быть больше 0")
            
        data = await state.get_data()
        currency = data['payout_currency']
        max_amount = data['max_amount']
        
        if amount > max_amount:
            await message.answer(
                f"❌ Недостаточно средств. Максимальная сумма: {max_amount:.2f}",
                reply_markup=get_back_to_balance_keyboard()
            )
            return
            
        currency_info = get_currency_info(currency)
        
        # Переходим к вводу реквизитов
        text = f"� <b>Запрос выплаты</b>\n\n"
        text += f"Валюта: {currency_info['name']}\n"
        text += f"Сумма: {amount:.2f} {currency_info['symbol']}\n\n"
        text += "💳 <b>Введите реквизиты для перевода:</b>\n"
        text += "• Номер карты или счета\n"
        text += "• ФИО получателя\n"
        text += "• Банк (если необходимо)\n\n"
        text += "<i>Пример:\n"
        text += "4169 1234 5678 9012\n"
        text += "Иванов Иван Иванович\n"
        text += "Сбербанк</i>"
        
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_back_to_balance_keyboard()
        )
        await state.set_state(BoosterStates.entering_payment_details)
        await state.update_data(payout_amount=amount)
        
    except ValueError:
        await message.answer(
            "❌ Введите корректную сумму (только цифры)",
            reply_markup=get_back_to_balance_keyboard()
        )

@router.message(BoosterStates.entering_payment_details)
@booster_only
async def process_payment_details(message: Message, state: FSMContext):
    """Обработка введенных реквизитов"""
    from app.keyboards.booster.payout_keyboards import get_payout_confirmation_keyboard
    
    try:
        payment_details = message.text.strip()
        
        if len(payment_details) < 10:
            await message.answer(
                "❌ Реквизиты слишком короткие. Пожалуйста, укажите полную информацию.",
                reply_markup=get_back_to_balance_keyboard()
            )
            return
            
        data = await state.get_data()
        currency = data['payout_currency']
        amount = data['payout_amount']
        
        currency_info = get_currency_info(currency)
        
        # Показываем подтверждение
        text = f"💸 <b>Подтверждение запроса выплаты</b>\n\n"
        text += f"Валюта: {currency_info['name']}\n"
        text += f"Сумма: {amount:.2f} {currency_info['symbol']}\n\n"
        text += f"💳 <b>Реквизиты:</b>\n"
        text += f"<code>{payment_details}</code>\n\n"
        text += "⚠️ После подтверждения сумма будет заморожена до обработки админом.\n\n"
        text += "Подтвердить запрос?"
        
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_payout_confirmation_keyboard(amount, currency)
        )
        await state.set_state(BoosterStates.confirming_payout_request)
        await state.update_data(payment_details=payment_details)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке реквизитов: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_balance_keyboard()
        )

@router.callback_query(F.data.startswith("confirm_payout_"))
@booster_only  
async def confirm_payout_request(call: CallbackQuery, state: FSMContext):
    """Подтверждение и создание запроса выплаты"""
    from app.keyboards.booster.payout_keyboards import get_payout_success_keyboard
    from app.database.crud import create_payout_request
    
    # Парсим данные из callback
    parts = call.data.split("_")
    amount = float(parts[2])
    currency = parts[3]
    
    # Получаем реквизиты из состояния
    data = await state.get_data()
    payment_details = data.get('payment_details', '')
    
    logger.info(f"Создание запроса выплаты от пользователя {call.from_user.id}: {amount} {currency}")
    
    # Создаем запрос в БД с реквизитами
    payout_request = await create_payout_request(call.from_user.id, amount, currency, payment_details)
    
    if payout_request:
        currency_info = get_currency_info(currency)
        
        text = f"✅ <b>Запрос выплаты создан</b>\n\n"
        text += f"📋 Номер запроса: #{payout_request.id}\n"
        text += f"💰 Сумма: {amount:.2f} {currency_info['symbol']}\n"
        text += f"📅 Дата: {payout_request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"💳 Реквизиты: <code>{payment_details}</code>\n\n"
        text += "⏳ Статус: Ожидает обработки\n\n"
        text += "📬 Уведомление отправлено администраторам. Ожидайте обработку."
        
        await call.message.edit_text(
            text,
            parse_mode="HTML", 
            reply_markup=get_payout_success_keyboard()
        )
        
        # Отправляем уведомление админам
        try:
            from app.utils.payments import notify_admins_about_payout_request
            from app.database.crud import get_booster_account_by_id
            from aiogram import Bot
            from app.config import BOT_TOKEN
            
            # Получаем данные аккаунта бустера
            booster_account = await get_booster_account_by_id(payout_request.booster_account_id)
            
            if booster_account:
                bot = Bot(token=BOT_TOKEN)
                await notify_admins_about_payout_request(bot, payout_request, booster_account)
                await bot.session.close()
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админам: {e}")
        
        logger.info(f"Создан запрос выплаты #{payout_request.id} для пользователя {call.from_user.id}")
        
    else:
        await call.answer("❌ Ошибка при создании запроса", show_alert=True)
        
    await state.clear()

@router.callback_query(F.data == "cancel_payout")
@booster_only
async def cancel_payout_request(call: CallbackQuery, state: FSMContext):
    """Отмена запроса выплаты"""
    await state.clear()
    account = await crud.get_booster_account(call.from_user.id)
    if account:
        await show_balance_menu(call, account, edit=True)
    else:
        await call.answer("❌ Аккаунт не найден", show_alert=True)

@router.callback_query(F.data == "my_payout_requests") 
@booster_only
async def show_my_payout_requests(call: CallbackQuery):
    """Показать мои запросы на выплату с пагинацией"""
    try:
        await show_payout_requests_page(call, page=0)
    except Exception as e:
        logger.error(f"Ошибка при показе запросов на выплату: {e}")
        await call.answer("❌ Ошибка загрузки запросов", show_alert=True)

@router.callback_query(F.data.startswith("payout_requests_page_"))
@booster_only
async def show_payout_requests_page(call: CallbackQuery, page: int = None):
    """Показать страницу запросов на выплату"""
    from app.keyboards.booster.payout_keyboards import get_payout_requests_list_keyboard
    from app.database.crud import get_user_payout_requests
    
    if page is None:
        page = int(call.data.split("_")[-1])
    
    requests = await get_user_payout_requests(call.from_user.id)
    
    if not requests:
        text = "📋 <b>Мои запросы на выплату</b>\n\n"
        text += "У вас пока нет запросов на выплату.\n\n"
        text += "💸 Создайте новый запрос, чтобы вывести заработанные средства."
        
        from app.keyboards.booster.payout_keyboards import get_my_requests_keyboard
        keyboard = get_my_requests_keyboard()
    else:
        total_requests = len(requests)
        text = f"📋 <b>Мои запросы на выплату</b>\n\n"
        text += f"📊 Всего запросов: {total_requests}\n"
        text += f"📄 Выберите запрос для просмотра:"
        
        keyboard = get_payout_requests_list_keyboard(requests, page)
    
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await call.answer()  # Отвечаем на callback в случае успеха
    except Exception as e:
        # Если не удалось изменить сообщение (например, это было фото), удаляем и отправляем новое
        if ("message can't be edited" in str(e) or 
            "message to edit not found" in str(e) or
            "there is no text in the message to edit" in str(e)):
            try:
                await call.message.delete()
                await call.message.bot.send_message(
                    call.from_user.id,
                    text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                await call.answer()  # Отвечаем на callback после успешного восстановления
            except Exception as delete_error:
                logger.error(f"Ошибка при удалении и отправке нового сообщения: {delete_error}")
                await call.answer("❌ Ошибка при загрузке списка")
        elif "message is not modified" in str(e):
            await call.answer("🔄 Данные актуальны")
        else:
            logger.error(f"Ошибка при обновлении сообщения с запросами: {e}")
            # Пробуем удалить и отправить новое сообщение
            try:
                await call.message.delete()
                await call.message.bot.send_message(
                    call.from_user.id,
                    text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                await call.answer()  # Отвечаем на callback после успешного fallback
            except Exception as fallback_error:
                logger.error(f"Ошибка fallback отправки: {fallback_error}")
                await call.answer("❌ Ошибка при загрузке списка")

@router.callback_query(F.data.startswith("view_payout_request_"))
@booster_only
async def view_payout_request_detail(call: CallbackQuery):
    """Показать детали запроса на выплату"""
    from app.keyboards.booster.payout_keyboards import get_payout_request_detail_keyboard
    from app.database.crud import get_payout_request_by_id
    
    request_id = int(call.data.split("_")[-1])
    payout_request = await get_payout_request_by_id(request_id)
    
    if not payout_request:
        await call.answer("❌ Запрос не найден", show_alert=True)
        return
    
    currency_info = get_currency_info(payout_request.currency)
    status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
    status_text = {"pending": "Ожидает обработки", "approved": "Одобрено", "rejected": "Отклонено"}
    
    text = f"📄 <b>Запрос на выплату #{payout_request.id}</b>\n\n"
    text += f"💰 Сумма: {payout_request.amount:.2f} {currency_info['symbol']}\n"
    text += f"💳 Валюта: {currency_info['name']}\n"
    text += f"📅 Создан: {payout_request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    text += f"{status_emoji.get(payout_request.status, '❓')} Статус: {status_text.get(payout_request.status, payout_request.status)}\n"
    
    if payout_request.payment_details:
        text += f"\n💳 <b>Реквизиты:</b>\n<code>{payout_request.payment_details}</code>\n"
    
    # Проверяем наличие и валидность updated_at
    if hasattr(payout_request, 'updated_at') and payout_request.updated_at and payout_request.updated_at != payout_request.created_at:
        text += f"\n📝 Обновлен: {payout_request.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
    
    if payout_request.admin_comment:
        text += f"\n💬 Комментарий: {payout_request.admin_comment}\n"
    
    keyboard = get_payout_request_detail_keyboard(payout_request.id)
    
    # Если есть чек - отправляем фото с текстом как подпись
    if payout_request.status == "approved" and payout_request.receipt_file_id:
        text += f"\n📄 <b>Чек о переводе:</b>"
        
        try:
            await call.message.delete()  # Удаляем предыдущее сообщение
            await call.message.bot.send_photo(
                call.from_user.id,
                payout_request.receipt_file_id,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await call.answer()  # Отвечаем на callback
            return  # Выходим, чтобы не отправлять текстовое сообщение
        except Exception as e:
            logger.error(f"Ошибка отправки чека: {e}")
            text += f"\n⚠️ Ошибка загрузки чека"
    
    # Если чека нет - отправляем обычное текстовое сообщение
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await call.answer()  # Отвечаем на callback
    except Exception as e:
        logger.error(f"Ошибка при показе деталей запроса: {e}")
        await call.answer("❌ Ошибка при загрузке деталей")

@router.callback_query(F.data == "return_to_payout_list")
@booster_only
async def return_to_payout_list(call: CallbackQuery):
    """Возврат к списку запросов выплат"""
    from app.keyboards.booster.payout_keyboards import get_payout_requests_list_keyboard, get_my_requests_keyboard
    from app.database.crud import get_user_payout_requests
    
    requests = await get_user_payout_requests(call.from_user.id)
    
    if not requests:
        text = "📋 <b>Мои запросы на выплату</b>\n\n"
        text += "У вас пока нет запросов на выплату.\n\n"
        text += "💸 Создайте новый запрос, чтобы вывести заработанные средства."
        keyboard = get_my_requests_keyboard()
    else:
        total_requests = len(requests)
        text = f"📋 <b>Мои запросы на выплату</b>\n\n"
        text += f"📊 Всего запросов: {total_requests}\n"
        text += f"📄 Выберите запрос для просмотра:"
        keyboard = get_payout_requests_list_keyboard(requests, page=0)
    
    # Всегда удаляем предыдущее сообщение и отправляем новое
    try:
        await call.message.delete()
        await call.message.bot.send_message(
            call.from_user.id,
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await call.answer()  # Отвечаем на callback чтобы убрать уведомление
    except Exception as e:
        logger.error(f"Ошибка при возврате к списку запросов: {e}")
        await call.answer("❌ Ошибка при загрузке списка")

@router.callback_query(F.data == "noop")
async def noop_handler(call: CallbackQuery):
    """Обработчик для кнопок без действия"""
    await call.answer()

@router.callback_query(F.data == "show_balance")
@booster_only
async def handle_show_balance(call: CallbackQuery):
    """Обработчик кнопки 'К балансу'"""
    account = await crud.get_booster_account(call.from_user.id)
    if account:
        await show_balance_menu(call, account, edit=True)
    else:
        await call.answer("❌ Аккаунт не найден", show_alert=True)

@router.callback_query(F.data == "back_to_balance")
@booster_only
async def handle_back_to_balance(call: CallbackQuery):
    """Обработчик кнопки 'Назад к балансу'"""
    account = await crud.get_booster_account(call.from_user.id)
    if account:
        await show_balance_menu(call, account, edit=True)
    else:
        await call.answer("❌ Аккаунт не найден", show_alert=True)

# === CONVERSION MENU HANDLERS ===

@router.callback_query(F.data == "booster_convert_menu")
@booster_only
async def show_convert_menu(call: CallbackQuery):
    """Показать меню выбора валюты для конвертации"""
    await call.message.edit_text(
        "💱 <b>Выберите валюту для конвертации</b>",
        parse_mode="HTML",
        reply_markup=booster_convert_menu_keyboard()
    )

@router.callback_query(F.data == "booster_cancel_convert_menu")
@booster_only
async def cancel_convert_menu(call: CallbackQuery):
    """Вернуться к основному меню баланса"""
    booster_account, user = await get_booster_data(call.from_user.id)
    
    if not booster_account or not user:
        await call.answer("❌ Ошибка получения данных", show_alert=True)
        return
    
    await show_balance_menu(call, booster_account, edit=True)

# === CONVERSION PROCESS HANDLERS ===

@router.callback_query(F.data.startswith("booster_convert_to:"))
@booster_only
async def handle_convert_selection(call: CallbackQuery, state: FSMContext):
    """Обработка выбора валюты для конвертации"""
    target_region = call.data.split(":")[1]
    logger.info(f"Пользователь {call.from_user.id} выбрал конвертацию в {target_region}")
    
    booster_account, _ = await get_booster_data(call.from_user.id)
    
    if not booster_account or booster_account.balance_usd <= 0:
        await call.answer("❌ У вас нет USD для конвертации", show_alert=True)
        return
    
    currency_info = get_local_currency_info()
    currency_name = currency_info["region_names"].get(target_region, "валюту")
    
    # Сохраняем данные в состояние
    await state.update_data(convert_target_region=target_region)
    await state.set_state(BoosterStates.entering_convert_amount)
    
    text = f"💱 <b>Конвертация в {currency_name}</b>\n\n"
    text += f"💵 Доступно: <b>{booster_account.balance_usd:.2f} USD</b>\n\n"
    text += f"Введите сумму в USD для конвертации в {currency_name}:"
    
    await call.message.edit_text(text, parse_mode="HTML")
    await call.answer()

@router.message(BoosterStates.entering_convert_amount)
@booster_only
async def process_convert_amount(message: Message, state: FSMContext):
    """Обработка ввода суммы для конвертации"""
    logger.info(f"Пользователь {message.from_user.id} ввел сумму: {message.text}")
    
    # Валидация суммы
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
    except ValueError:
        await message.answer("❌ Введите корректную сумму (например: 10 или 10.5)")
        return
    
    # Проверка баланса
    booster_account, _ = await get_booster_data(message.from_user.id)
    if not booster_account or amount > booster_account.balance_usd:
        await message.answer("❌ Недостаточно средств на USD балансе")
        return
    
    # Получение данных конвертации
    data = await state.get_data()
    target_region = data.get("convert_target_region")
    currency_info = get_local_currency_info()
    currency_name = currency_info["region_names"].get(target_region)
    currency_code = currency_info["currency_codes"].get(target_region)
    
    try:
        from app.utils.currency_converter import convert_booster_balance
        
        logger.info(f"Конвертация: {amount} USD -> {currency_code}")
        converted_amount = await convert_booster_balance(amount, "USD", currency_code)
        logger.info(f"Результат конвертации: {converted_amount} {currency_code}")
        
        # Сохраняем данные для подтверждения
        await state.update_data(
            convert_amount_usd=amount,
            converted_amount=converted_amount,
            currency_code=currency_code
        )
        
        text = f"💱 <b>Подтверждение конвертации</b>\n\n"
        text += f"💵 Сумма к конвертации: <b>{amount:.2f} USD</b>\n"
        text += f"💰 Вы получите: <b>{converted_amount:.2f} {currency_code}</b>\n\n"
        text += "Подтвердить конвертацию?"
        
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=conversion_confirm_keyboard(target_region)
        )
        
    except Exception as e:
        logger.error(f"Ошибка конвертации для пользователя {message.from_user.id}: {e}")
        await message.answer("❌ Ошибка при расчете конвертации. Попробуйте позже.")
        await state.clear()

@router.callback_query(F.data.startswith("booster_confirm_convert:"))
@booster_only 
async def confirm_conversion(call: CallbackQuery, state: FSMContext):
    """Подтверждение и выполнение конвертации"""
    logger.info(f"Подтверждение конвертации от пользователя {call.from_user.id}")
    
    # Получение данных из состояния
    data = await state.get_data()
    required_fields = ["convert_target_region", "convert_amount_usd", "converted_amount", "currency_code"]
    
    if not all(data.get(field) for field in required_fields):
        await call.answer("❌ Ошибка данных конвертации", show_alert=True)
        await state.clear()
        return
    
    target_region = data["convert_target_region"]
    amount_usd = data["convert_amount_usd"]
    converted_amount = data["converted_amount"]
    currency_code = data["currency_code"]
    
    try:
        from app.database.crud import update_booster_balance_conversion
        
        logger.info(f"Выполнение конвертации в БД: {amount_usd} USD -> {converted_amount} {currency_code}")
        success = await update_booster_balance_conversion(
            call.from_user.id,
            amount_usd,
            converted_amount,
            target_region
        )
        
        if success:
            text = f"✅ <b>Конвертация выполнена!</b>\n\n"
            text += f"💵 Списано: {amount_usd:.2f} USD\n"
            text += f"💰 Зачислено: {converted_amount:.2f} {currency_code}"
            
            await call.message.edit_text(text, parse_mode="HTML")
            logger.info(f"Успешная конвертация для пользователя {call.from_user.id}: {amount_usd} USD -> {converted_amount} {currency_code}")
        else:
            await call.answer("❌ Ошибка при выполнении конвертации", show_alert=True)
            logger.error(f"Не удалось выполнить конвертацию в БД для пользователя {call.from_user.id}")
            
    except Exception as e:
        logger.error(f"Исключение при конвертации для пользователя {call.from_user.id}: {e}")
        await call.answer("❌ Ошибка при выполнении конвертации", show_alert=True)
    
    await state.clear()

@router.callback_query(F.data == "booster_cancel_convert")
@booster_only
async def cancel_conversion(call: CallbackQuery, state: FSMContext):
    """Отмена конвертации"""
    await state.clear()
    await call.message.edit_text(
        "❌ Конвертация отменена",
        reply_markup=None
    )
    logger.info(f"Пользователь {call.from_user.id} отменил конвертацию")