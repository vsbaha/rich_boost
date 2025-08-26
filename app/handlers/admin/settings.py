import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.utils.roles import admin_only
from app.utils.settings import SettingsManager, DEFAULT_SETTINGS
from app.states.admin_states import AdminStates
from app.config import REGION_CURRENCIES
import json

router = Router()
logger = logging.getLogger(__name__)

# Категории настроек
SETTINGS_CATEGORIES = {
    "backup": "📁 Бэкап",
    "payments": "💰 Платежи",
    "prices": "💎 Цены"
}

def settings_menu_keyboard():
    """Главное меню настроек"""
    keyboard = []
    for category, name in SETTINGS_CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"settings_category:{category}")])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Сбросить всё", callback_data="settings_reset_all")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def category_settings_keyboard(category: str, settings: dict):
    """Клавиатура для настроек определенной категории"""
    keyboard = []
    
    for key, config in DEFAULT_SETTINGS.items():
        if config["category"] == category:
            current_value = settings.get(key, config["value"])
            
            # Создаем компактное описание
            description = config['description']
            if len(description) > 25:
                description = description[:22] + "..."
            
            # Сокращаем отображение значений
            if isinstance(current_value, dict):
                display_value = "📝"
            elif isinstance(current_value, (int, float)):
                display_value = str(current_value)
            else:
                value_str = str(current_value)
                display_value = value_str[:10] + "..." if len(value_str) > 10 else value_str
            
            # Ограничиваем общую длину кнопки
            button_text = f"{description}: {display_value}"
            if len(button_text) > 35:
                button_text = f"{description[:20]}...: {display_value}"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"setting_edit:{key}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def price_regions_keyboard(setting_key: str, edit_type: str):
    """Клавиатура выбора региона для редактирования цен"""
    keyboard = []
    for region in ["🇰🇬 КР", "🇰🇿 КЗ", "🇷🇺 РУ"]:
        currency = REGION_CURRENCIES.get(region, "")
        keyboard.append([InlineKeyboardButton(
            text=f"{region} ({currency})", 
            callback_data=f"price_region:{edit_type}:{setting_key}:{region}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"setting_edit:{setting_key}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def rank_prices_keyboard(region: str, setting_key: str, current_prices: dict):
    """Клавиатура для редактирования цен рангов"""
    keyboard = []
    region_prices = current_prices.get(region, {})
    
    # Обычные ранги
    regular_ranks = ["Воин", "Элита", "Мастер", "Грандмастер", "Эпик", "Легенда", "Мифик"]
    for rank in regular_ranks:
        price = region_prices.get(rank, 0)
        keyboard.append([InlineKeyboardButton(
            text=f"{rank}: {price}", 
            callback_data=f"price_edit_rank:{setting_key}:{region}:{rank}"
        )])
    
    # Мифик звезды
    mythic_ranges = ["Мифик0-25", "Мифик25-50", "Мифик50-100", "Мифик100+"]
    for range_name in mythic_ranges:
        price = region_prices.get(range_name, 0)
        keyboard.append([InlineKeyboardButton(
            text=f"{range_name}: {price}", 
            callback_data=f"price_edit_rank:{setting_key}:{region}:{range_name}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ К регионам", callback_data=f"price_edit_ranks:{setting_key}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def coaching_prices_keyboard(setting_key: str, current_prices: dict):
    """Клавиатура для редактирования цен обучения"""
    keyboard = []
    
    for region in ["🇰🇬 КР", "🇰🇿 КЗ", "🇷🇺 РУ"]:
        price = current_prices.get(region, 0)
        currency = REGION_CURRENCIES.get(region, "")
        keyboard.append([InlineKeyboardButton(
            text=f"{region}: {price} {currency}/час", 
            callback_data=f"price_edit_coaching_region:{setting_key}:{region}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"setting_edit:{setting_key}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def multipliers_keyboard(setting_key: str, current_multipliers: dict):
    """Клавиатура для редактирования множителей"""
    keyboard = []
    
    multiplier_names = {
        "account": "🔐 Аккаунт",
        "shared": "👥 Общий",
        "winrate": "📈 Винрейт",
        "mmr": "🎯 MMR",
        "coaching": "🎓 Обучение"
    }
    
    for key, name in multiplier_names.items():
        value = current_multipliers.get(key, 1.0)
        keyboard.append([InlineKeyboardButton(
            text=f"{name}: x{value}", 
            callback_data=f"price_edit_multiplier:{setting_key}:{key}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"setting_edit:{setting_key}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def setting_edit_keyboard(key: str):
    """Клавиатура для редактирования конкретной настройки"""
    keyboard = []
    
    # Специальные кнопки для цен
    if key in ["RANK_PRICES", "COACHING_PRICES", "BOOST_MULTIPLIERS"]:
        if key == "RANK_PRICES":
            keyboard.append([InlineKeyboardButton(text="💎 Редактировать цены", callback_data=f"price_edit_ranks:{key}")])
        elif key == "COACHING_PRICES":
            keyboard.append([InlineKeyboardButton(text="🎓 Редактировать обучение", callback_data=f"price_edit_coaching:{key}")])
        elif key == "BOOST_MULTIPLIERS":
            keyboard.append([InlineKeyboardButton(text="⚡ Редактировать множители", callback_data=f"price_edit_multipliers:{key}")])
    else:
        keyboard.append([InlineKeyboardButton(text="✏️ Изменить", callback_data=f"setting_change:{key}")])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Сбросить", callback_data=f"setting_reset:{key}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"settings_category:{DEFAULT_SETTINGS[key]['category']}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(F.text == "🎯 Настройки")
@admin_only
async def settings_main_menu(message: Message):
    """Главное меню настроек"""
    logger.info(f"Админ @{message.from_user.username} открыл настройки")
    
    text = (
        "🎯 <b>Настройки бота</b>\n\n"
        "Выберите категорию для настройки:"
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=settings_menu_keyboard())

@router.callback_query(F.data == "settings_main")
@admin_only
async def settings_main_callback(call: CallbackQuery):
    """Возврат к главному меню настроек"""
    text = (
        "🎯 <b>Настройки бота</b>\n\n"
        "Выберите категорию для настройки:"
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=settings_menu_keyboard())
    await call.answer()

@router.callback_query(F.data.startswith("settings_category:"))
@admin_only
async def settings_category_menu(call: CallbackQuery):
    """Меню настроек определенной категории"""
    category = call.data.split(":")[1]
    category_name = SETTINGS_CATEGORIES.get(category, category)
    
    logger.info(f"Админ @{call.from_user.username} открыл категорию настроек: {category}")
    
    # Получаем текущие настройки
    current_settings = await SettingsManager.get_all_settings(category)
    
    # Специальный текст для категории цен
    if category == "prices":
        text = await generate_prices_summary()
    else:
        text = f"⚙️ <b>{category_name}</b>\n\nТекущие настройки:"
    
    await call.message.edit_text(
        text, 
        parse_mode="HTML", 
        reply_markup=category_settings_keyboard(category, current_settings)
    )
    await call.answer()

async def generate_prices_summary():
    """Генерирует сводку актуальных цен"""
    # Получаем данные о ценах
    rank_prices = await SettingsManager.get_setting("RANK_PRICES")
    coaching_prices = await SettingsManager.get_setting("COACHING_PRICES")
    multipliers = await SettingsManager.get_setting("BOOST_MULTIPLIERS")
    
    text = "💎 <b>Сводка актуальных цен</b>\n\n"
    
    # Сводка по обучению
    text += "🎓 <b>Обучение (за час):</b>\n"
    for region in ["🇰🇬 КР", "🇰🇿 КЗ", "🇷🇺 РУ"]:
        price = coaching_prices.get(region, 0)
        currency = REGION_CURRENCIES.get(region, "")
        text += f"• {region}: {price} {currency}\n"
    
    # Сводка по основным рангам для разных регионов
    text += f"\n🏆 <b>Основные ранги:</b>\n"
    for region in ["🇰🇬 КР", "🇰🇿 КЗ", "🇷🇺 РУ"]:
        region_prices = rank_prices.get(region, {})
        price = region_prices.get("Воин", 0)  # Берем цену Воина как базовую
        currency = REGION_CURRENCIES.get(region, "")
        text += f"• {region}: {price} {currency} (за ранг)\n"
    
    # Мифик звезды для КР как пример
    text += f"\n⭐ <b>Мифик звезды (пример для 🇰🇬 КР):</b>\n"
    kg_prices = rank_prices.get("🇰🇬 КР", {})
    mythic_ranges = [
        ("0-25 звезд", "Мифик0-25"),
        ("25-50 звезд", "Мифик25-50"), 
        ("50-100 звезд", "Мифик50-100"),
        ("100+ звезд", "Мифик100+")
    ]
    for display_name, key in mythic_ranges:
        price = kg_prices.get(key, 0)
        text += f"• {display_name}: {price} сом\n"
    
    # Множители
    text += f"\n⚡ <b>Множители буста:</b>\n"
    multiplier_names = {
        "account": "🔐 Аккаунт",
        "shared": "👥 Общий", 
        "winrate": "📈 Винрейт",
        "mmr": "🎯 MMR",
        "coaching": "🎓 Обучение"
    }
    for key, name in multiplier_names.items():
        value = multipliers.get(key, 1.0)
        text += f"• {name}: x{value}\n"
    
    text += f"\n📝 <i>Нажмите на настройку для редактирования</i>"
    
    return text

@router.callback_query(F.data.startswith("setting_edit:"))
@admin_only
async def setting_edit_menu(call: CallbackQuery):
    """Меню редактирования конкретной настройки"""
    key = call.data.split(":")[1]
    
    if key not in DEFAULT_SETTINGS:
        await call.answer("Настройка не найдена", show_alert=True)
        return
    
    config = DEFAULT_SETTINGS[key]
    current_value = await SettingsManager.get_setting(key)
    
    # Специальное отображение для цен
    if key in ["RANK_PRICES", "COACHING_PRICES", "BOOST_MULTIPLIERS"]:
        if key == "RANK_PRICES":
            value_display = "Используйте редактор для удобной настройки цен по регионам и рангам"
        elif key == "COACHING_PRICES":
            value_display = "Используйте редактор для настройки цен обучения по регионам"
        elif key == "BOOST_MULTIPLIERS":
            value_display = "Используйте редактор для настройки множителей буста"
    else:
        # Обычное отображение для других настроек
        if isinstance(current_value, dict):
            value_display = json.dumps(current_value, indent=2, ensure_ascii=False)
        else:
            value_display = str(current_value)
    
    text = (
        f"⚙️ <b>{config['description']}</b>\n\n"
        f"📝 <b>Значение:</b>\n"
        f"<code>{value_display}</code>\n\n"
        f"� {SETTINGS_CATEGORIES.get(config['category'], config['category'])}"
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=setting_edit_keyboard(key))
    await call.answer()

@router.callback_query(F.data.startswith("setting_change:"))
@admin_only
async def setting_change_start(call: CallbackQuery, state: FSMContext):
    """Начало изменения настройки"""
    key = call.data.split(":")[1]
    
    if key not in DEFAULT_SETTINGS:
        await call.answer("Настройка не найдена", show_alert=True)
        return
    
    config = DEFAULT_SETTINGS[key]
    current_value = await SettingsManager.get_setting(key)
    
    await state.update_data(setting_key=key)
    
    # Форматируем текущее значение для отображения
    if isinstance(current_value, dict):
        value_display = json.dumps(current_value, indent=2, ensure_ascii=False)
        instruction = "Отправьте новое значение в формате JSON:"
    else:
        value_display = str(current_value)
        instruction = "Отправьте новое значение:"
    
    text = (
        f"✏️ <b>Изменение настройки</b>\n\n"
        f"📝 <b>{config['description']}</b>\n"
        f"📋 <b>Сейчас:</b>\n"
        f"<code>{value_display}</code>\n\n"
        f"{instruction}"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"setting_edit:{key}")]
        ]
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_setting_value)
    await call.answer()

@router.message(AdminStates.waiting_for_setting_value)
@admin_only
async def setting_change_process(message: Message, state: FSMContext):
    """Обработка нового значения настройки"""
    data = await state.get_data()
    
    # Проверяем, это обычная настройка или цена
    if "price_setting_key" in data:
        await process_price_change(message, state, data)
    else:
        await process_regular_setting_change(message, state, data)

async def process_price_change(message: Message, state: FSMContext, data: dict):
    """Обработка изменения цены"""
    setting_key = data.get("price_setting_key")
    price_type = data.get("price_type")
    new_value_str = message.text.strip()
    
    try:
        if price_type == "multiplier":
            new_value = float(new_value_str)
            if new_value <= 0:
                await message.answer("❌ Множитель должен быть больше 0")
                return
        else:
            new_value = int(new_value_str)
            if new_value <= 0:
                await message.answer("❌ Цена должна быть больше 0")
                return
        
        # Получаем текущие настройки
        current_settings = await SettingsManager.get_setting(setting_key)
        
        if price_type == "rank":
            region = data.get("price_region")
            rank = data.get("price_rank")
            
            if region not in current_settings:
                current_settings[region] = {}
            current_settings[region][rank] = new_value
            
            success_msg = f"✅ Цена для {rank} в {region} изменена на {new_value}"
            callback_data = f"price_region:ranks:{setting_key}:{region}"
            
        elif price_type == "coaching":
            region = data.get("price_region")
            current_settings[region] = new_value
            
            currency = REGION_CURRENCIES.get(region, "")
            success_msg = f"✅ Цена обучения в {region} изменена на {new_value} {currency}/час"
            callback_data = f"price_edit_coaching:{setting_key}"
            
        elif price_type == "multiplier":
            multiplier_key = data.get("price_multiplier_key")
            current_settings[multiplier_key] = new_value
            
            success_msg = f"✅ Множитель изменен на x{new_value}"
            callback_data = f"price_edit_multipliers:{setting_key}"
        
        # Сохраняем обновленные настройки
        config = DEFAULT_SETTINGS[setting_key]
        success = await SettingsManager.set_setting(
            setting_key,
            current_settings,
            config["description"],
            config["category"]
        )
        
        if success:
            logger.info(f"Админ @{message.from_user.username} изменил цену {setting_key}: {data}")
            await message.answer(
                success_msg,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)]
                    ]
                )
            )
        else:
            await message.answer("❌ Ошибка при сохранении")
            
    except (ValueError, TypeError):
        await message.answer(
            "❌ Неправильный формат числа\n\n"
            "Введите корректное число (например: 100 или 1.5)"
        )
        return
    
    await state.clear()

async def process_regular_setting_change(message: Message, state: FSMContext, data: dict):
    """Обработка обычной настройки (существующий код)"""
    key = data.get("setting_key")
    
    if not key or key not in DEFAULT_SETTINGS:
        await message.answer("Ошибка: настройка не найдена")
        await state.clear()
        return
    
    config = DEFAULT_SETTINGS[key]
    new_value_str = message.text.strip()
    
    try:
        # Пытаемся парсить как JSON если это сложный тип
        if isinstance(config["value"], (dict, list)):
            new_value = json.loads(new_value_str)
        elif isinstance(config["value"], int):
            new_value = int(new_value_str)
        elif isinstance(config["value"], float):
            new_value = float(new_value_str)
        elif isinstance(config["value"], bool):
            new_value = new_value_str.lower() in ('true', '1', 'да', 'yes')
        else:
            new_value = new_value_str
        
        # Сохраняем настройку
        success = await SettingsManager.set_setting(
            key, 
            new_value, 
            config["description"], 
            config["category"]
        )
        
        if success:
            logger.info(f"Админ @{message.from_user.username} изменил настройку {key}: {new_value}")
            await message.answer(
                f"✅ Настройка '{config['description']}' успешно обновлена!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⚙️ К настройкам", callback_data=f"setting_edit:{key}")]
                    ]
                )
            )
        else:
            await message.answer("❌ Ошибка при сохранении настройки")
        
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        await message.answer(
            f"❌ Ошибка формата данных: {str(e)}\n\n"
            "Проверьте правильность введенного значения."
        )
        return
    
    await state.clear()

@router.callback_query(F.data.startswith("setting_reset:"))
@admin_only
async def setting_reset(call: CallbackQuery):
    """Сброс настройки к значению по умолчанию"""
    key = call.data.split(":")[1]
    
    if key not in DEFAULT_SETTINGS:
        await call.answer("Настройка не найдена", show_alert=True)
        return
    
    config = DEFAULT_SETTINGS[key]
    success = await SettingsManager.set_setting(
        key,
        config["value"],
        config["description"],
        config["category"]
    )
    
    if success:
        logger.info(f"Админ @{call.from_user.username} сбросил настройку {key} к умолчанию")
        await call.answer("✅ Настройка сброшена к значению по умолчанию")
        
        # Обновляем отображение
        current_value = config["value"]
        if isinstance(current_value, dict):
            value_display = json.dumps(current_value, indent=2, ensure_ascii=False)
        else:
            value_display = str(current_value)
        
        text = (
            f"⚙️ <b>{config['description']}</b>\n\n"
            f"📝 <b>Текущее значение:</b>\n"
            f"<code>{value_display}</code>\n\n"
            f"📋 <b>Категория:</b> {SETTINGS_CATEGORIES.get(config['category'], config['category'])}"
        )
        
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=setting_edit_keyboard(key))
    else:
        await call.answer("❌ Ошибка при сбросе настройки", show_alert=True)

@router.callback_query(F.data == "settings_reset_all")
@admin_only
async def settings_reset_all_confirm(call: CallbackQuery):
    """Подтверждение сброса всех настроек"""
    text = (
        "⚠️ <b>Внимание!</b>\n\n"
        "Сбросить ВСЕ настройки к умолчанию?\n\n"
        "❗ Действие необратимо!"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="settings_reset_all_confirm"),
                InlineKeyboardButton(text="❌ Нет", callback_data="settings_main")
            ]
        ]
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

@router.callback_query(F.data == "settings_reset_all_confirm")
@admin_only
async def settings_reset_all_process(call: CallbackQuery):
    """Выполнение сброса всех настроек"""
    try:
        for key, config in DEFAULT_SETTINGS.items():
            await SettingsManager.set_setting(
                key,
                config["value"],
                config["description"],
                config["category"]
            )
        
        logger.info(f"Админ @{call.from_user.username} сбросил все настройки к умолчанию")
        
        text = (
            "✅ <b>Успешно!</b>\n\n"
            "Все настройки сброшены к значениям по умолчанию."
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ К настройкам", callback_data="settings_main")]
            ]
        )
        
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await call.answer()
        
    except Exception as e:
        logger.error(f"Ошибка сброса настроек: {e}")
        await call.answer("❌ Ошибка при сбросе настроек", show_alert=True)

@router.callback_query(F.data == "settings_back")
@admin_only
async def settings_back_to_admin(call: CallbackQuery):
    """Возврат в админ-панель"""
    await call.message.delete()
    await call.message.answer(
        "Добро пожаловать в админ-панель!",
        reply_markup=admin_menu_keyboard()
    )
    await call.answer()

# Обработчики для редактирования цен

@router.callback_query(F.data.startswith("price_edit_ranks:"))
@admin_only
async def price_edit_ranks_menu(call: CallbackQuery):
    """Меню выбора региона для редактирования цен рангов"""
    setting_key = call.data.split(":")[1]
    
    text = (
        "💎 <b>Редактирование цен рангов</b>\n\n"
        "Выберите регион для настройки:"
    )
    
    await call.message.edit_text(
        text, 
        parse_mode="HTML", 
        reply_markup=price_regions_keyboard(setting_key, "ranks")
    )
    await call.answer()

@router.callback_query(F.data.startswith("price_region:ranks:"))
@admin_only
async def price_region_ranks_menu(call: CallbackQuery):
    """Меню редактирования цен рангов для конкретного региона"""
    parts = call.data.split(":")
    setting_key = parts[2]
    region = parts[3]
    
    current_prices = await SettingsManager.get_setting(setting_key)
    currency = REGION_CURRENCIES.get(region, "")
    
    text = (
        f"💎 <b>Цены рангов - {region}</b>\n\n"
        f"Валюта: {currency}\n"
        "Выберите ранг для изменения цены:"
    )
    
    await call.message.edit_text(
        text, 
        parse_mode="HTML", 
        reply_markup=rank_prices_keyboard(region, setting_key, current_prices)
    )
    await call.answer()

@router.callback_query(F.data.startswith("price_edit_rank:"))
@admin_only
async def price_edit_rank_start(call: CallbackQuery, state: FSMContext):
    """Начало редактирования цены конкретного ранга"""
    parts = call.data.split(":")
    setting_key = parts[1]
    region = parts[2]
    rank = parts[3]
    
    current_prices = await SettingsManager.get_setting(setting_key)
    current_price = current_prices.get(region, {}).get(rank, 0)
    currency = REGION_CURRENCIES.get(region, "")
    
    await state.update_data(
        price_setting_key=setting_key,
        price_region=region,
        price_rank=rank,
        price_type="rank"
    )
    
    text = (
        f"✏️ <b>Изменение цены ранга</b>\n\n"
        f"🏆 <b>Ранг:</b> {rank}\n"
        f"🌍 <b>Регион:</b> {region}\n"
        f"💰 <b>Текущая цена:</b> {current_price} {currency}\n\n"
        f"Введите новую цену:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"price_region:ranks:{setting_key}:{region}")]
        ]
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_setting_value)
    await call.answer()

@router.callback_query(F.data.startswith("price_edit_coaching:"))
@admin_only
async def price_edit_coaching_menu(call: CallbackQuery):
    """Меню редактирования цен обучения"""
    setting_key = call.data.split(":")[1]
    current_prices = await SettingsManager.get_setting(setting_key)
    
    text = (
        "🎓 <b>Цены обучения</b>\n\n"
        "Выберите регион для изменения цены:"
    )
    
    await call.message.edit_text(
        text, 
        parse_mode="HTML", 
        reply_markup=coaching_prices_keyboard(setting_key, current_prices)
    )
    await call.answer()

@router.callback_query(F.data.startswith("price_edit_coaching_region:"))
@admin_only
async def price_edit_coaching_region_start(call: CallbackQuery, state: FSMContext):
    """Начало редактирования цены обучения для региона"""
    parts = call.data.split(":")
    setting_key = parts[1]
    region = parts[2]
    
    current_prices = await SettingsManager.get_setting(setting_key)
    current_price = current_prices.get(region, 0)
    currency = REGION_CURRENCIES.get(region, "")
    
    await state.update_data(
        price_setting_key=setting_key,
        price_region=region,
        price_type="coaching"
    )
    
    text = (
        f"✏️ <b>Изменение цены обучения</b>\n\n"
        f"🌍 <b>Регион:</b> {region}\n"
        f"💰 <b>Текущая цена:</b> {current_price} {currency}/час\n\n"
        f"Введите новую цену за час:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"price_edit_coaching:{setting_key}")]
        ]
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_setting_value)
    await call.answer()

@router.callback_query(F.data.startswith("price_edit_multipliers:"))
@admin_only
async def price_edit_multipliers_menu(call: CallbackQuery):
    """Меню редактирования множителей"""
    setting_key = call.data.split(":")[1]
    current_multipliers = await SettingsManager.get_setting(setting_key)
    
    text = (
        "⚡ <b>Множители буста</b>\n\n"
        "Выберите тип для изменения множителя:"
    )
    
    await call.message.edit_text(
        text, 
        parse_mode="HTML", 
        reply_markup=multipliers_keyboard(setting_key, current_multipliers)
    )
    await call.answer()

@router.callback_query(F.data.startswith("price_edit_multiplier:"))
@admin_only
async def price_edit_multiplier_start(call: CallbackQuery, state: FSMContext):
    """Начало редактирования множителя"""
    parts = call.data.split(":")
    setting_key = parts[1]
    multiplier_key = parts[2]
    
    current_multipliers = await SettingsManager.get_setting(setting_key)
    current_value = current_multipliers.get(multiplier_key, 1.0)
    
    multiplier_names = {
        "account": "🔐 Аккаунт",
        "shared": "👥 Общий",
        "winrate": "📈 Винрейт",
        "mmr": "🎯 MMR",
        "coaching": "🎓 Обучение"
    }
    
    multiplier_name = multiplier_names.get(multiplier_key, multiplier_key)
    
    await state.update_data(
        price_setting_key=setting_key,
        price_multiplier_key=multiplier_key,
        price_type="multiplier"
    )
    
    text = (
        f"✏️ <b>Изменение множителя</b>\n\n"
        f"⚡ <b>Тип:</b> {multiplier_name}\n"
        f"📊 <b>Текущий множитель:</b> x{current_value}\n\n"
        f"Введите новый множитель (например: 1.5):"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"price_edit_multipliers:{setting_key}")]
        ]
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_setting_value)
    await call.answer()

from app.keyboards.admin.admin_menu import admin_menu_keyboard
