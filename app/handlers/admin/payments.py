from app.database.crud import get_payment_request_by_id, update_payment_request_status, get_user_by_id, update_user_balance_by_region, get_user_by_tg_id, get_all_payment_requests
from aiogram import Router, F
import logging
from app.config import PAGE_SIZE
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from app.utils.roles import admin_only
from app.utils.user import format_user_profile
from app.states.admin_states import SearchStates
from app.keyboards.admin.payments import admin_topup_action_keyboard, back_to_payment_keyboard

router = Router()
logger = logging.getLogger(__name__)

def format_payment_request_text(payment_request, user):
    status = payment_request.status
    status_text = '✅ Принято' if status == 'accepted' else '❌ Отклонено' if status == 'rejected' else '⏳ В ожидании'
    return (
        f"<b>Заявка на пополнение</b>\n"
        f"ID: <code>{payment_request.id}</code>\n"
        f"Пользователь: @{user.username or '—'}\n"
        f"User ID: <code>{user.tg_id}</code>\n"
        f"Регион: {payment_request.region}\n"
        f"Сумма: {payment_request.amount:.2f}\n"
        f"Дата: {payment_request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Статус: {status_text}"
    )

@router.message(F.text == "💸 Все заявки на пополнение")
@admin_only
async def admin_all_topup_requests(message: Message):
    logger.info(f"Админ @{message.from_user.username or 'без username'} открыл меню всех заявок на пополнение")
    requests = await get_all_payment_requests()
    if not requests:
        logger.info(f"Админ @{message.from_user.username or 'без username'}: нет заявок на пополнение")
        await message.answer("Нет заявок на пополнение.")
        return

    filter_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏳ В ожидании", callback_data="filter_topups:pending"),
                InlineKeyboardButton(text="✅ Принятые", callback_data="filter_topups:accepted"),
                InlineKeyboardButton(text="❌ Отклонённые", callback_data="filter_topups:rejected"),
            ],
            [
                InlineKeyboardButton(text="🔎 Поиск по ID", callback_data="search_by_id")
            ]
        ]
    )

    text = "<b>Все заявки на пополнение:</b>\nВыберите заявку для подробностей:"
    await message.answer(text, parse_mode="HTML", reply_markup=filter_keyboard)
    logger.info("Показано меню фильтрации заявок")

@router.callback_query(F.data.startswith("filter_topups:"))
@admin_only
async def filter_topup_requests(call: CallbackQuery):
    status = call.data.split(":")[1]
    logger.info(f"Админ @{call.from_user.username or 'без username'} выбрал фильтр заявок: {status}")
    await show_filtered_requests(call, status, page=1)

@router.callback_query(F.data.startswith("admin_topup_info:"))
@admin_only
async def admin_topup_info(call: CallbackQuery):
    parts = call.data.split(":")
    request_id = int(parts[1])
    filter_status = parts[2] if len(parts) > 2 else "pending"
    from_list = len(parts) > 3 and parts[3] == "from_list"
    payment_request = await get_payment_request_by_id(request_id)
    user = await get_user_by_id(payment_request.user_id)
    text = format_payment_request_text(payment_request, user)
    keyboard = admin_topup_action_keyboard(
        request_id,
        payment_request.status,
        filter_status,
        user_tg_id=user.tg_id,
        from_list=from_list
    )
    try:
        await call.message.delete()
    except Exception as e:
        logger.warning(f"Сообщение уже удалено или не удалось удалить: {e}")
    if payment_request.receipt_file_id:
        await call.message.answer_photo(
            photo=payment_request.receipt_file_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    logger.info(f"Админ @{call.from_user.username or 'без username'} просмотрел заявку на пополнение ID {request_id}")
    await call.answer()

@router.callback_query(F.data.startswith("accept_payment:"))
@admin_only
async def accept_payment(call: CallbackQuery):
    parts = call.data.split(":")
    request_id = int(parts[1])
    filter_status = parts[3] if len(parts) > 3 else "pending"
    from_list = len(parts) > 4 and parts[4] == "from_list"
    payment_request = await get_payment_request_by_id(request_id)
    if payment_request.status != "pending":
        logger.info(f"Админ @{call.from_user.username or 'без username'} попытался принять уже обработанную заявку ID {request_id}")
        await call.answer("Заявка уже обработана!", show_alert=True)
        return
    user = await get_user_by_id(payment_request.user_id)
    await update_user_balance_by_region(user, payment_request.region, payment_request.amount)
    await update_payment_request_status(request_id, "accepted")
    logger.info(f"Админ @{call.from_user.username or 'без username'} принял заявку на пополнение ID {request_id}")
    await call.answer("Пополнение принято!")
    try:
        await call.bot.send_message(
            user.tg_id,
            f"✅ Ваша заявка на пополнение {payment_request.amount:.2f} {payment_request.region} принята! Баланс пополнен."
        )
        logger.info(f"Пользователь {user.tg_id} уведомлен о принятии заявки")
    except Exception as e:
        logger.warning(f"Админ @{call.from_user.username or 'без username'}: не удалось уведомить пользователя {user.tg_id}: {e}")
    if from_list:
        await show_filtered_requests(call, filter_status, page=1)
    else:
        try:
            await call.message.delete()
        except Exception as e:
            logger.warning(f"Админ @{call.from_user.username or 'без username'}: сообщение уже удалено или не удалось удалить: {e}")

@router.callback_query(F.data.startswith("reject_payment:"))
@admin_only
async def reject_payment(call: CallbackQuery):
    parts = call.data.split(":")
    request_id = int(parts[1])
    filter_status = parts[3] if len(parts) > 3 else "pending"
    from_list = len(parts) > 4 and parts[4] == "from_list"
    payment_request = await get_payment_request_by_id(request_id)
    if payment_request.status != "pending":
        logger.info(f"Админ @{call.from_user.username or 'без username'} попытался отклонить уже обработанную заявку ID {request_id}")
        await call.answer("Заявка уже обработана!", show_alert=True)
        return
    await update_payment_request_status(request_id, "rejected")
    user = await get_user_by_id(payment_request.user_id)
    logger.info(f"Админ @{call.from_user.username or 'без username'} отклонил заявку на пополнение ID {request_id}")
    await call.answer("Пополнение отклонено!")
    try:
        await call.bot.send_message(
            user.tg_id,
            f"❌ Ваша заявка на пополнение {payment_request.amount:.2f} {payment_request.region} отклонена."
        )
        logger.info(f"Пользователь {user.tg_id} уведомлен об отклонении заявки")
    except Exception as e:
        logger.warning(f"Админ @{call.from_user.username or 'без username'}: не удалось уведомить пользователя {user.tg_id}: {e}")
    if from_list:
        await show_filtered_requests(call, filter_status, page=1)
    else:
        try:
            await call.message.delete()
        except Exception as e:
            logger.warning(f"Админ @{call.from_user.username or 'без username'}: сообщение уже удалено или не удалось удалить: {e}")

@router.callback_query(F.data.startswith("back_to_filtered:"))
@admin_only
async def back_to_filtered(call: CallbackQuery):
    filter_status = call.data.split(":")[1]
    logger.info(f"Админ @{call.from_user.username or 'без username'} вернулся к списку заявок со статусом {filter_status}")
    await show_filtered_requests(call, filter_status, page=1)

@router.callback_query(F.data.startswith("payment_user_info:"))
@admin_only
async def payment_user_info(call: CallbackQuery):
    parts = call.data.split(":")
    user_tg_id = int(parts[1])
    request_id = int(parts[2])
    user = await get_user_by_tg_id(user_tg_id)
    if not user:
        logger.warning(f"Админ @{call.from_user.username or 'без username'} попытался посмотреть профиль несуществующего пользователя {user_tg_id}")
        await call.answer("Пользователь не найден.", show_alert=True)
        return
    try:
        await call.message.delete()
    except Exception as e:
        logger.warning(f"Сообщение уже удалено или не удалось удалить: {e}")
    await call.message.answer(
        format_user_profile(user),
        parse_mode="HTML",
        reply_markup=back_to_payment_keyboard(request_id, user)
    )
    logger.info(f"Админ @{call.from_user.username or 'без username'} просмотрел профиль пользователя {user_tg_id}")
    await call.answer()

@router.callback_query(F.data.startswith("back_to_payment:"))
@admin_only
async def back_to_payment(call: CallbackQuery):
    request_id = int(call.data.split(":")[1])
    payment_request = await get_payment_request_by_id(request_id)
    user = await get_user_by_id(payment_request.user_id)
    status = payment_request.status
    filter_status = "pending"
    keyboard = admin_topup_action_keyboard(request_id, status, filter_status, user_tg_id=user.tg_id)
    text = format_payment_request_text(payment_request, user)
    try:
        await call.message.delete()
    except Exception as e:
        logger.warning(f"Сообщение уже удалено или не удалось удалить: {e}")
    if payment_request.receipt_file_id:
        await call.message.answer_photo(
            photo=payment_request.receipt_file_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    logger.info(f"Админ @{call.from_user.username or 'без username'} вернулся к заявке на пополнение ID {request_id}")
    await call.answer()

@router.callback_query(F.data.startswith("admin_requests_page:"))
@admin_only
async def admin_requests_page(call: CallbackQuery):
    parts = call.data.split(":")
    filter_status = parts[1]
    page = int(parts[2])
    logger.info(f"Админ @{call.from_user.username or 'без username'} переключил страницу заявок: статус={filter_status}, страница={page}")
    await show_filtered_requests(call, filter_status, page)

async def show_filtered_requests(call: CallbackQuery, filter_status: str, page: int = 1):
    requests = await get_all_payment_requests()
    filtered = [r for r in requests if r.status == filter_status]
    total_pages = (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE
    if not filtered:
        try:
            await call.message.edit_text("Нет заявок с таким статусом.")
        except Exception as e:
            if "there is no text in the message to edit" not in str(e):
                logger.warning(f"Админ @{call.from_user.username or 'без username'}: не удалось отредактировать сообщение: {e}")
            try:
                await call.message.delete()
                await call.message.answer("Нет заявок с таким статусом.")
            except Exception as e2:
                logger.warning(f"Админ @{call.from_user.username or 'без username'}: не удалось удалить/отправить сообщение: {e2}")
        logger.info(f"Админ @{call.from_user.username or 'без username'} увидел пустой список заявок со статусом {filter_status}")
        await call.answer()
        return
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_requests = filtered[start:end]
    text = f"<b>Заявки со статусом: {filter_status}</b>\nСтраница {page}/{total_pages}\nВыберите заявку для подробностей:"
    buttons = [
        [
            InlineKeyboardButton(
                text=f"ID: {req.id} | "
                    f"{req.created_at.strftime('%d.%m.%Y %H:%M')} | "
                    f"{req.amount:.2f} | {req.region} | User ID: {req.user_id}",
                callback_data=f"admin_topup_info:{req.id}:{filter_status}:from_list"
            )
        ] for req in page_requests
    ]
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_requests_page:{filter_status}:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"admin_requests_page:{filter_status}:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    requests_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=requests_keyboard)
    except Exception as e:
        if "there is no text in the message to edit" not in str(e):
            logger.warning(f"Админ @{call.from_user.username or 'без username'}: не удалось отредактировать сообщение: {e}")
        try:
            await call.message.delete()
            await call.message.answer(text, parse_mode="HTML", reply_markup=requests_keyboard)
        except Exception as e2:
            logger.warning(f"Админ @{call.from_user.username or 'без username'}: не удалось удалить/отправить сообщение: {e2}")
    logger.info(f"Админ @{call.from_user.username or 'без username'} просмотрел заявки: статус={filter_status}, страница={page}")
    await call.answer()

@router.callback_query(F.data == "search_by_id")
@admin_only
async def ask_order_id(call: CallbackQuery, state: FSMContext):
    logger.info(f"Админ @{call.from_user.username or 'без username'} выбрал поиск заявки по ID")
    await call.message.edit_text(
        "Введите ID заказа для поиска:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filter_menu")]
            ]
        )
    )
    await state.set_state(SearchStates.waiting_for_id)
    await call.answer()

@router.callback_query(F.data == "back_to_filter_menu")
@admin_only
async def back_to_filter_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    filter_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏳ В ожидании", callback_data="filter_topups:pending"),
                InlineKeyboardButton(text="✅ Принятые", callback_data="filter_topups:accepted"),
                InlineKeyboardButton(text="❌ Отклонённые", callback_data="filter_topups:rejected"),
            ],
            [
                InlineKeyboardButton(text="🔎 Поиск по ID", callback_data="search_by_id")
            ]
        ]
    )
    try:
        await call.message.edit_text(
            "<b>Все заявки на пополнение:</b>\nВыберите заявку для подробностей:",
            parse_mode="HTML",
            reply_markup=filter_keyboard
        )
    except Exception as e:
        if "there is no text in the message to edit" not in str(e):
            logger.warning(f"Админ @{call.from_user.username or 'без username'}: не удалось отредактировать сообщение: {e}")
        try:
            await call.message.delete()
            await call.message.answer(
                "<b>Все заявки на пополнение:</b>\nВыберите заявку для подробностей:",
                parse_mode="HTML",
                reply_markup=filter_keyboard
            )
        except Exception as e2:
            logger.warning(f"Админ @{call.from_user.username or 'без username'}: не удалось удалить/отправить сообщение: {e2}")
    logger.info(f"Админ @{call.from_user.username or 'без username'} вернулся к меню фильтрации заявок")
    await call.answer()

@router.message(SearchStates.waiting_for_id)
@admin_only
async def search_order_by_id(message: Message, state: FSMContext):
    logger.info(f"Админ @{message.from_user.username or 'без username'} ввёл ID для поиска заявки")
    if not message.text.isdigit():
        logger.info(f"Админ @{message.from_user.username or 'без username'} ввёл некорректный ID (не число)")
        await message.answer(
            "Пожалуйста, введите числовой ID заказа.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_filter_menu")]
                ]
            )
        )
        return
    request_id = int(message.text)
    payment_request = await get_payment_request_by_id(request_id)
    if not payment_request:
        logger.info(f"Админ @{message.from_user.username or 'без username'}: заявка с ID {request_id} не найдена")
        await message.answer(
            "Заявка с таким ID не найдена.\nПопробуйте ввести другой ID заказа или нажмите 'Отмена'.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_filter_menu")]
                ]
            )
        )
        return
    user = await get_user_by_id(payment_request.user_id)
    text = format_payment_request_text(payment_request, user)
    keyboard = admin_topup_action_keyboard(
        payment_request.id,
        payment_request.status,
        "pending",
        user_tg_id=user.tg_id,
        from_list=False
    )
    if payment_request.receipt_file_id:
        await message.answer_photo(
            photo=payment_request.receipt_file_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logger.info(f"Админ @{message.from_user.username or 'без username'} нашёл заявку по ID {request_id} (с фото)")
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        logger.info(f"Админ @{message.from_user.username or 'без username'} нашёл заявку по ID {request_id} (без фото)")
    await state.clear()