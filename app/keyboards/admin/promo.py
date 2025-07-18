from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def promo_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Скидка (%)", callback_data="promo_type:discount"),
                InlineKeyboardButton(text="Бонус (сумма)", callback_data="promo_type:bonus")
            ]
        ]
    )

def promo_currency_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="сом", callback_data="promo_currency:сом"),
                InlineKeyboardButton(text="тенге", callback_data="promo_currency:тенге"),
                InlineKeyboardButton(text="руб.", callback_data="promo_currency:руб.")
            ]
        ]
    )

def promo_onetime_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Одноразовый", callback_data="promo_onetime:yes"),
                InlineKeyboardButton(text="Многоразовый", callback_data="promo_onetime:no")
            ]
        ]
    )

def promo_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="promo_confirm:yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="promo_confirm:no")
            ]
        ]
    )

def cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="promo_cancel")]
        ]
    )

def promo_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Активные промокоды", callback_data="promo_active"),
                InlineKeyboardButton(text="➕ Создать промокод", callback_data="promo_create")
            ],
            [
                InlineKeyboardButton(text="🔍 Поиск промокода", callback_data="promo_search")
            ]
        ]
    )

def promo_list_keyboard(promos, page, total_pages):
    keyboard = [
        [InlineKeyboardButton(text=f"{p.code}", callback_data=f"promo_manage:{p.id}")]
        for p in promos
    ]
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"promo_page:{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="promo_page:cur"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"promo_page:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="promo_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def promo_manage_keyboard(promo):
    # promo: object or dict with .id and .is_active
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"promo_delete:{promo.id}")
            ],
            [
                InlineKeyboardButton(
                    text="🧊 Заморозить" if promo.is_active else "✅ Разморозить",
                    callback_data=f"promo_toggle:{promo.id}"
                )
            ],
            [
                InlineKeyboardButton(text="⬅️ К списку", callback_data="promo_active")
            ]
        ]
    )