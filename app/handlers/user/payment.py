from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.states.user_states import OrderStates
from app.keyboards.user.payment_keyboards import (
    payment_method_keyboard, payment_confirmation_keyboard, 
    bonus_amount_keyboard, discount_info_keyboard
)
from app.keyboards.user.order_keyboards import confirm_order_keyboard
from app.database.crud import (
    get_user_by_id, get_user_active_discount, apply_user_discount,
    get_user_bonus_balance, use_user_bonus
)
import logging

router = Router()
logger = logging.getLogger(__name__)


def get_currency_from_region(region: str) -> str:
    """Получает валюту по региону"""
    if "🇰🇬" in region or region == "KG":
        return "сом"
    elif "🇰🇿" in region or region == "KZ":
        return "тенге"
    elif "🇷🇺" in region or region == "RU":
        return "руб."
    else:
        return "сом"


def get_user_balance_by_region(user, region: str) -> float:
    """Получает баланс пользователя по региону"""
    if "🇰🇬" in region or region == "KG":
        return float(user.balance_kg or 0)
    elif "🇰🇿" in region or region == "KZ":
        return float(user.balance_kz or 0)
    elif "🇷🇺" in region or region == "RU":
        return float(user.balance_ru or 0)
    else:
        return float(user.balance_kg or 0)


@router.callback_query(F.data == "choose_payment_method")
async def choose_payment_method(call: CallbackQuery, state: FSMContext):
    """Показ способов оплаты"""
    logger.info(f"Пользователь @{call.from_user.username} выбирает способ оплаты")
    
    data = await state.get_data()
    user_id = data.get("user_id")
    region = data.get("region")
    base_cost = data.get("total_cost", 0)
    
    if not user_id or not region or base_cost <= 0:
        await call.answer("Ошибка: не хватает данных заказа", show_alert=True)
        return
    
    # Получаем пользователя
    user = await get_user_by_id(user_id)
    if not user:
        await call.answer("Пользователь не найден", show_alert=True)
        return
    
    # Получаем валюту
    currency = get_currency_from_region(region)
    
    # Проверяем активную скидку
    discount_percent = await get_user_active_discount(user_id)
    has_discount = discount_percent > 0
    
    # Рассчитываем финальную стоимость с учетом скидки
    final_cost = base_cost
    if has_discount:
        final_cost = base_cost * (1 - discount_percent / 100)
        await state.update_data(
            discount_percent=discount_percent,
            discounted_cost=final_cost
        )
    
    # Получаем балансы
    user_balance = get_user_balance_by_region(user, region)
    bonus_balance = await get_user_bonus_balance(user_id, currency)
    
    # Сохраняем данные об оплате
    await state.update_data(
        final_cost=final_cost,
        original_cost=base_cost,
        currency=currency,
        user_balance=user_balance,
        bonus_balance=bonus_balance,
        has_discount=has_discount
    )
    
    # Формируем текст
    text = f"💳 <b>Выбор способа оплаты</b>\n\n"
    text += f"🛒 <b>Стоимость заказа:</b> {base_cost:.0f} {currency}\n"
    
    if has_discount:
        text += f"🎁 <b>Скидка:</b> {discount_percent}% (-{base_cost - final_cost:.0f} {currency})\n"
        text += f"💰 <b>К оплате:</b> {final_cost:.0f} {currency}\n\n"
    else:
        text += f"💰 <b>К оплате:</b> {final_cost:.0f} {currency}\n\n"
    
    text += f"💳 <b>Баланс:</b> {user_balance:.0f} {currency}\n"
    text += f"🎁 <b>Бонусы:</b> {bonus_balance:.0f} {currency}\n\n"
    text += "Выберите способ оплаты:"
    
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=payment_method_keyboard(
            final_cost, user_balance, bonus_balance, currency, has_discount
        )
    )
    
    await state.set_state(OrderStates.payment_selection)
    await call.answer()


@router.callback_query(F.data == "pay_full_balance")
async def pay_full_balance(call: CallbackQuery, state: FSMContext):
    """Оплата полностью с баланса"""
    await show_payment_confirmation(call, state, "balance", "💳 с баланса")


@router.callback_query(F.data == "pay_full_bonus")
async def pay_full_bonus(call: CallbackQuery, state: FSMContext):
    """Оплата полностью бонусами"""
    await show_payment_confirmation(call, state, "bonus", "🎁 бонусами")


@router.callback_query(F.data == "pay_mixed")
async def pay_mixed(call: CallbackQuery, state: FSMContext):
    """Смешанная оплата (все бонусы + доплата с баланса)"""
    data = await state.get_data()
    bonus_balance = data.get("bonus_balance", 0)
    final_cost = data.get("final_cost", 0)
    remaining = final_cost - bonus_balance
    currency = data.get("currency", "сом")
    
    await state.update_data(
        payment_method="mixed",
        bonus_amount=bonus_balance,
        balance_amount=remaining
    )
    
    await show_payment_confirmation(
        call, state, "mixed", 
        f"🎭 смешанно ({bonus_balance:.0f} {currency} бонусами + {remaining:.0f} {currency} с баланса)"
    )


@router.callback_query(F.data == "pay_partial_bonus")
async def pay_partial_bonus(call: CallbackQuery, state: FSMContext):
    """Выбор суммы бонусов для частичной оплаты"""
    data = await state.get_data()
    bonus_balance = data.get("bonus_balance", 0)
    final_cost = data.get("final_cost", 0)
    currency = data.get("currency", "сом")
    
    # Максимально можно использовать бонусов не больше стоимости заказа
    max_bonus = min(bonus_balance, final_cost)
    
    text = f"💰 <b>Частичная оплата бонусами</b>\n\n"
    text += f"🎁 <b>Доступно бонусов:</b> {bonus_balance:.0f} {currency}\n"
    text += f"💳 <b>К оплате:</b> {final_cost:.0f} {currency}\n\n"
    text += "Выберите сумму бонусов для использования:"
    
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=bonus_amount_keyboard(max_bonus, currency)
    )
    
    await state.set_state(OrderStates.bonus_amount_input)
    await call.answer()


@router.callback_query(F.data.startswith("bonus_amount:"))
async def select_bonus_amount(call: CallbackQuery, state: FSMContext):
    """Выбор предустановленной суммы бонусов"""
    bonus_amount = float(call.data.split(":")[1])
    await process_bonus_amount(call, state, bonus_amount)


@router.callback_query(F.data == "custom_bonus_amount")
async def custom_bonus_amount_input(call: CallbackQuery, state: FSMContext):
    """Ввод пользовательской суммы бонусов"""
    data = await state.get_data()
    bonus_balance = data.get("bonus_balance", 0)
    final_cost = data.get("final_cost", 0)
    currency = data.get("currency", "сом")
    
    max_bonus = min(bonus_balance, final_cost)
    
    await call.message.edit_text(
        f"✏️ <b>Ввод суммы бонусов</b>\n\n"
        f"🎁 <b>Доступно бонусов:</b> {bonus_balance:.0f} {currency}\n"
        f"💳 <b>К оплате:</b> {final_cost:.0f} {currency}\n\n"
        f"Введите сумму бонусов (максимум {max_bonus:.0f} {currency}):",
        parse_mode="HTML"
    )
    
    await call.answer()


@router.message(OrderStates.bonus_amount_input)
async def process_custom_bonus_amount(message: Message, state: FSMContext):
    """Обработка пользовательского ввода суммы бонусов"""
    try:
        bonus_amount = float(message.text.replace(",", "."))
        
        if bonus_amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
            
        # Получаем данные для проверки лимитов
        data = await state.get_data()
        bonus_balance = data.get("bonus_balance", 0)
        final_cost = data.get("final_cost", 0)
        max_bonus = min(bonus_balance, final_cost)
        
        if bonus_amount > max_bonus:
            currency = data.get("currency", "сом")
            await message.answer(
                f"❌ Превышен лимит!\n"
                f"Максимум: {max_bonus:.0f} {currency}"
            )
            return
        
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        # Создаем фиктивный CallbackQuery для обработки
        from types import SimpleNamespace
        fake_call = SimpleNamespace()
        fake_call.message = message
        fake_call.answer = lambda text="", show_alert=False: None
        
        await process_bonus_amount(fake_call, state, bonus_amount)
        
    except ValueError:
        await message.answer("❌ Введите корректное число")


async def process_bonus_amount(call, state: FSMContext, bonus_amount: float):
    """Обработка выбранной суммы бонусов"""
    data = await state.get_data()
    final_cost = data.get("final_cost", 0)
    user_balance = data.get("user_balance", 0)
    currency = data.get("currency", "сом")
    
    remaining_cost = final_cost - bonus_amount
    
    # Проверяем, хватает ли баланса для доплаты
    if remaining_cost > user_balance:
        text = f"❌ <b>Недостаточно средств</b>\n\n"
        text += f"🎁 <b>Бонусы:</b> {bonus_amount:.0f} {currency}\n"
        text += f"💳 <b>Доплата с баланса:</b> {remaining_cost:.0f} {currency}\n"
        text += f"💰 <b>На балансе:</b> {user_balance:.0f} {currency}\n"
        text += f"❗ <b>Не хватает:</b> {remaining_cost - user_balance:.0f} {currency}\n\n"
        text += "Выберите меньшую сумму бонусов или пополните баланс."
        
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=bonus_amount_keyboard(
                min(data.get("bonus_balance", 0), final_cost), currency
            )
        )
        return
    
    # Сохраняем данные об оплате
    await state.update_data(
        payment_method="partial_bonus",
        bonus_amount=bonus_amount,
        balance_amount=remaining_cost
    )
    
    if remaining_cost > 0:
        payment_desc = f"🎭 частично ({bonus_amount:.0f} {currency} бонусами + {remaining_cost:.0f} {currency} с баланса)"
    else:
        payment_desc = f"🎁 полностью бонусами ({bonus_amount:.0f} {currency})"
    
    await show_payment_confirmation(call, state, "partial_bonus", payment_desc)


async def show_payment_confirmation(call, state: FSMContext, method: str, method_description: str):
    """Показ подтверждения способа оплаты"""
    data = await state.get_data()
    final_cost = data.get("final_cost", 0)
    currency = data.get("currency", "сом")
    has_discount = data.get("has_discount", False)
    discount_percent = data.get("discount_percent", 0)
    original_cost = data.get("original_cost", final_cost)
    
    # Формируем текст подтверждения
    text = f"✅ <b>Подтверждение оплаты</b>\n\n"
    
    if has_discount:
        text += f"🛒 <b>Изначальная стоимость:</b> {original_cost:.0f} {currency}\n"
        text += f"🎁 <b>Скидка:</b> {discount_percent}% (-{original_cost - final_cost:.0f} {currency})\n"
        text += f"💰 <b>Итого к оплате:</b> {final_cost:.0f} {currency}\n\n"
    else:
        text += f"💰 <b>К оплате:</b> {final_cost:.0f} {currency}\n\n"
    
    text += f"💳 <b>Способ оплаты:</b> {method_description}\n\n"
    
    # Добавляем детали для частичной оплаты
    if method in ["partial_bonus", "mixed"]:
        bonus_amount = data.get("bonus_amount", 0)
        balance_amount = data.get("balance_amount", 0)
        text += f"🔹 Бонусами: {bonus_amount:.0f} {currency}\n"
        text += f"🔹 С баланса: {balance_amount:.0f} {currency}\n\n"
    
    text += "Подтвердите оплату для создания заказа:"
    
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=payment_confirmation_keyboard(method)
    )
    
    await call.answer()


@router.callback_query(F.data == "discount_info")
async def show_discount_info(call: CallbackQuery, state: FSMContext):
    """Информация об активной скидке"""
    data = await state.get_data()
    discount_percent = data.get("discount_percent", 0)
    original_cost = data.get("original_cost", 0)
    final_cost = data.get("final_cost", 0)
    currency = data.get("currency", "сом")
    
    text = f"🎁 <b>Ваша активная скидка</b>\n\n"
    text += f"📊 <b>Размер скидки:</b> {discount_percent}%\n"
    text += f"💰 <b>Экономия:</b> {original_cost - final_cost:.0f} {currency}\n\n"
    text += "Скидка будет автоматически применена при оплате этого заказа.\n"
    text += "После использования скидка сгорит."
    
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=discount_info_keyboard()
    )
    
    await call.answer()


@router.callback_query(F.data == "change_payment_method")
async def change_payment_method(call: CallbackQuery, state: FSMContext):
    """Возврат к выбору способа оплаты"""
    await choose_payment_method(call, state)


@router.callback_query(F.data == "back_to_payment_methods")
async def back_to_payment_methods(call: CallbackQuery, state: FSMContext):
    """Возврат к способам оплаты"""
    await choose_payment_method(call, state)


@router.callback_query(F.data == "back_to_order_confirm")
async def back_to_order_confirm(call: CallbackQuery, state: FSMContext):
    """Возврат к подтверждению заказа"""
    data = await state.get_data()
    
    # Пересчитываем стоимость без скидки для отображения
    original_cost = data.get("total_cost", 0)
    currency = data.get("currency", "сом")
    
    # Показываем стандартное подтверждение заказа
    from app.handlers.user.create_order import show_order_confirmation
    await show_order_confirmation(call, state)
    
    await call.answer()
