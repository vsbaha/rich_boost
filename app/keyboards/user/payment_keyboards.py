from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def payment_method_keyboard(total_cost: float, user_balance: float, bonus_balance: float, currency: str, has_discount: bool = False):
    """Клавиатура выбора способа оплаты"""
    keyboard = []
    
    # Показываем информацию о скидке
    if has_discount:
        keyboard.append([
            InlineKeyboardButton(text="🎁 У вас есть активная скидка!", callback_data="discount_info")
        ])
    
    # Оплата полностью с баланса
    if user_balance >= total_cost:
        keyboard.append([
            InlineKeyboardButton(
                text=f"💳 Оплатить с баланса ({total_cost:.0f} {currency})",
                callback_data="pay_full_balance"
            )
        ])
    
    # Оплата полностью бонусами
    if bonus_balance >= total_cost:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🎁 Оплатить бонусами ({total_cost:.0f} {currency})",
                callback_data="pay_full_bonus"
            )
        ])
    
    # Частичная оплата бонусами
    if bonus_balance > 0 and bonus_balance < total_cost:
        remaining = total_cost - bonus_balance
        if user_balance >= remaining:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🎭 Смешанная оплата",
                    callback_data="pay_mixed"
                )
            ])
        keyboard.append([
            InlineKeyboardButton(
                text=f"💰 Использовать часть бонусов",
                callback_data="pay_partial_bonus"
            )
        ])
    
    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад к заказу", callback_data="back_to_order_confirm")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def payment_confirmation_keyboard(payment_method: str):
    """Клавиатура подтверждения способа оплаты"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment:{payment_method}"),
            InlineKeyboardButton(text="❌ Изменить способ", callback_data="change_payment_method")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к заказу", callback_data="back_to_order_confirm")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def bonus_amount_keyboard(max_bonus: float, currency: str):
    """Клавиатура для выбора суммы бонусов"""
    keyboard = []
    
    # Предустановленные варианты (25%, 50%, 75%, максимум)
    if max_bonus >= 100:
        amounts = [
            (max_bonus * 0.25, "25%"),
            (max_bonus * 0.5, "50%"),
            (max_bonus * 0.75, "75%"),
            (max_bonus, "Все")
        ]
        
        for amount, label in amounts:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{label} — {amount:.0f} {currency}",
                    callback_data=f"bonus_amount:{amount:.0f}"
                )
            ])
    else:
        # Если бонусов мало, показываем только "Все"
        keyboard.append([
            InlineKeyboardButton(
                text=f"Все — {max_bonus:.0f} {currency}",
                callback_data=f"bonus_amount:{max_bonus:.0f}"
            )
        ])
    
    keyboard.extend([
        [InlineKeyboardButton(text="✏️ Ввести свою сумму", callback_data="custom_bonus_amount")],
        [InlineKeyboardButton(text="🔙 Назад к способам оплаты", callback_data="back_to_payment_methods")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def discount_info_keyboard():
    """Клавиатура с информацией о скидке"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад к оплате", callback_data="back_to_payment_methods")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
