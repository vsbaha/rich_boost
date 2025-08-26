from .models import User, Base, BoosterAccount, PaymentRequest
from sqlalchemy.future import select
from .models import Base
from .db import engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from datetime import datetime, timezone
import uuid
from aiogram import Bot
from app.config import BOT_TOKEN
from app.database.db import AsyncSessionLocal
from sqlalchemy import delete
from app.database.models import User, BonusHistory, PromoCode, PromoActivation, Order, BotSettings, BoosterAccount
import logging

logger = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Инициализируем настройки по умолчанию
    from app.utils.settings import SettingsManager
    await SettingsManager.initialize_default_settings()

async def add_user(tg_id, username, region=None, role="user", referrer_id=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            now = datetime.now(timezone.utc)
            user = User(
                tg_id=tg_id,
                username=username,
                region=region,
                role=role,
                created_at=now,
                referrer_id=referrer_id,
            )
            session.add(user)
            await session.commit()

async def update_user_region(tg_id: int, new_region: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.region = new_region
            await session.commit()

async def get_user_by_tg_id(tg_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()

async def update_user_username(tg_id, username):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user and user.username != username:
            user.username = username
            await session.commit()

async def get_booster_account(tg_id):
    async with AsyncSessionLocal() as session:
        # Сначала находим пользователя по telegram ID
        user_result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            return None
            
        # Затем ищем аккаунт бустера по ID пользователя
        result = await session.execute(select(BoosterAccount).where(BoosterAccount.user_id == user.id))
        return result.scalar_one_or_none()

async def create_booster_account(user_id, username, session):
    from app.database.models import BoosterAccount
    account = BoosterAccount(user_id=user_id, username=username)
    session.add(account)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()

async def update_booster_balance(user_id, amount, currency="руб."):
    """Обновляет баланс бустера в соответствующей валюте"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BoosterAccount).where(BoosterAccount.user_id == user_id))
        account = result.scalar_one_or_none()
        if account:
            # Определяем поле баланса по валюте
            currency_fields = {
                "сом": "balance_kg",
                "тенге": "balance_kz", 
                "руб.": "balance_ru"
            }
            balance_field = currency_fields.get(currency, "balance_ru")
            
            # Обновляем соответствующий баланс
            current_balance = getattr(account, balance_field, 0)
            setattr(account, balance_field, current_balance + amount)
            await session.commit()

async def get_booster_balance_by_region(user_id, region):
    """Получает баланс бустера в валюте его региона"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BoosterAccount).where(BoosterAccount.user_id == user_id))
        account = result.scalar_one_or_none()
        if account:
            region_balances = {
                "🇰🇬 КР": account.balance_kg,
                "🇰🇿 КЗ": account.balance_kz,
                "🇷🇺 РУ": account.balance_ru
            }
            return region_balances.get(region, account.balance_ru)
        return 0

async def get_booster_total_balance_in_currency(user_id, target_currency):
    """Получает общий баланс бустера, сконвертированный в указанную валюту"""
    from app.utils.currency_converter import convert_booster_balance
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BoosterAccount).where(BoosterAccount.user_id == user_id))
        account = result.scalar_one_or_none()
        if not account:
            return 0
        
        total_balance = 0
        
        # Конвертируем балансы из всех валют в целевую
        if account.balance_kg > 0:
            converted = await convert_booster_balance(account.balance_kg, "сом", target_currency)
            total_balance += converted
            
        if account.balance_kz > 0:
            converted = await convert_booster_balance(account.balance_kz, "тенге", target_currency)
            total_balance += converted
            
        if account.balance_ru > 0:
            converted = await convert_booster_balance(account.balance_ru, "руб.", target_currency)
            total_balance += converted
        
        return round(total_balance, 2)

async def convert_booster_balance_to_region(user_id, target_region):
    """Конвертирует весь баланс бустера в валюту указанного региона"""
    from app.utils.currency_converter import convert_booster_balance
    
    # Определяем целевую валюту
    region_currencies = {
        "🇰🇬 КР": "сом",
        "🇰🇿 КЗ": "тенге",
        "🇷🇺 РУ": "руб."
    }
    target_currency = region_currencies.get(target_region, "руб.")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BoosterAccount).where(BoosterAccount.user_id == user_id))
        account = result.scalar_one_or_none()
        if not account:
            return False, "Аккаунт бустера не найден"
        
        # Подсчитываем общий баланс в целевой валюте
        total_balance = 0
        
        # Конвертируем из всех валют
        if account.balance_kg > 0:
            converted = await convert_booster_balance(account.balance_kg, "сом", target_currency)
            total_balance += converted
            
        if account.balance_kz > 0:
            converted = await convert_booster_balance(account.balance_kz, "тенге", target_currency)
            total_balance += converted
            
        if account.balance_ru > 0:
            converted = await convert_booster_balance(account.balance_ru, "руб.", target_currency)
            total_balance += converted
        
        # Обнуляем все балансы и записываем в целевую валюту
        account.balance_kg = 0
        account.balance_kz = 0
        account.balance_ru = 0
        
        if target_currency == "сом":
            account.balance_kg = total_balance
        elif target_currency == "тенге":
            account.balance_kz = total_balance
        elif target_currency == "руб.":
            account.balance_ru = total_balance
            
        await session.commit()
        return True, f"Баланс успешно сконвертирован в {target_currency}: {total_balance:.2f}"

async def get_users_page(offset=0, limit=5):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).offset(offset).limit(limit))
        return result.scalars().all()

async def count_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(User))
        return result.scalar_one()

async def count_users_by_role(role: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(User).where(User.role == role))
        return result.scalar_one()

async def search_users(query: str):
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(
            or_(
                User.username.ilike(f"%{query}%"),
                User.tg_id == query if query.isdigit() else False
            )
        )
        result = await session.execute(stmt)
        return result.scalars().all()

async def update_user_balance(tg_id, new_balance, region=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            target_region = region or user.region
            if target_region == "🇰🇬 КР" or target_region == "kg":
                user.balance_kg = new_balance
            elif target_region == "🇰🇿 КЗ" or target_region == "kz":
                user.balance_kz = new_balance
            elif target_region == "🇷🇺 РУ" or target_region == "ru":
                user.balance_ru = new_balance
            await session.commit()

async def update_user_bonus_balance(tg_id, new_bonus_balance, region=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            target_region = region or user.region
            if target_region == "🇰🇬 КР" or target_region == "kg":
                user.bonus_kg = new_bonus_balance
            elif target_region == "🇰🇿 КЗ" or target_region == "kz":
                user.bonus_kz = new_bonus_balance
            elif target_region == "🇷🇺 РУ" or target_region == "ru":
                user.bonus_ru = new_bonus_balance
            await session.commit()

async def update_user_role(tg_id, new_role):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.role = new_role
            await session.commit()


async def create_payment_request(user_id, region, amount, receipt_file_id):
    async with AsyncSessionLocal() as session:
        request = PaymentRequest(
            user_id=user_id,
            region=region,
            amount=amount,
            receipt_file_id=receipt_file_id,
            status="pending"
        )
        session.add(request)
        await session.commit()
        await session.refresh(request)
        return request

async def get_payment_request_by_id(request_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PaymentRequest).where(PaymentRequest.id == request_id))
        return result.scalar_one_or_none()

async def update_payment_request_status(request_id, status):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PaymentRequest).where(PaymentRequest.id == request_id))
        request = result.scalar_one_or_none()
        if request:
            request.status = status
            await session.commit()

async def get_user_by_id(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

async def update_user_balance_by_region(user_id: int, balance_field: str, amount: float):
    """Обновление баланса пользователя по региону"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user_db = result.scalar_one_or_none()
        if user_db:
            # Проверяем первое пополнение только если amount положительный (пополнение)
            is_first_topup = False
            if amount > 0:
                is_first_topup = (
                    user_db.balance_kg == 0 and
                    user_db.balance_kz == 0 and
                    user_db.balance_ru == 0
                )
            
            # Обновляем баланс
            current_balance = getattr(user_db, balance_field)
            setattr(user_db, balance_field, current_balance + amount)
            
            await session.commit()

            # Если это первое пополнение — начисляем бонус пригласившему
            if is_first_topup and user_db.referrer_id:
                BONUS_AMOUNT = 50  # укажи нужную сумму
                await add_bonus_to_referrer(user_db.id, BONUS_AMOUNT)
            
            return getattr(user_db, balance_field)
        return None

async def get_admins():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.tg_id).where(User.role == "admin"))
        return [row[0] for row in result.all()]
    
async def get_payment_requests_by_user(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PaymentRequest).where(PaymentRequest.user_id == user_id).order_by(PaymentRequest.created_at.desc())
        )
        return result.scalars().all()
    
async def get_all_payment_requests():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PaymentRequest).order_by(PaymentRequest.created_at.desc())
        )
        return result.scalars().all()

from sqlalchemy import select

async def set_booster_status(user_id: int, status: str, session):
    result = await session.execute(
        select(BoosterAccount).where(BoosterAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account:
        account.status = status
        await session.commit()



async def add_bonus_to_referrer(user_id: int, amount: float):
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user and user.referrer_id:
            referrer = await session.get(User, user.referrer_id)
            if referrer:
                # Можно начислять в бонус_kg, бонус_kz, бонус_ru по региону реферала
                if user.region == "🇰🇬 КР":
                    referrer.bonus_kg += amount
                elif user.region == "🇰🇿 КЗ":
                    referrer.bonus_kz += amount
                elif user.region == "🇷🇺 РУ":
                    referrer.bonus_ru += amount
                await session.commit()

                # Добавляем запись в историю бонусов
                history = BonusHistory(
                    user_id=referrer.id,
                    amount=amount,
                    source="Реферал",
                    comment=(
                        f"Бонус за приглашённого пользователя "
                        f"{'@' + user.username if user.username else user.tg_id}"
                    )
                )
                session.add(history)
                await session.commit()

                if referrer.tg_id:
                    try:
                        await bot.send_message(
                            referrer.tg_id,
                            f"Вам начислен бонус {amount} за первое пополнение приглашённого пользователя!"
                        )
                    except Exception:
                        pass  # если пользователь заблокировал бота и т.д.

async def check_and_activate_promo(user_id: int, code: str):
    async with AsyncSessionLocal() as session:
        # Получаем промокод
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == code)
        )
        promo = result.scalar_one_or_none()
        if not promo:
            return False, "Промокод не найден."

        # Проверка срока действия
        if promo.expires_at:
            expires_at = promo.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return False, "Промокод не найден."

        # Проверка лимита активаций
        if promo.max_activations is not None and promo.activations >= promo.max_activations:
            return False, "Лимит активаций промокода исчерпан."

        # Проверка на повторную активацию по user_id и promo_code
        activation = await session.execute(
            select(PromoActivation).where(
                PromoActivation.user_id == user_id,
                PromoActivation.promo_code == promo.code
            )
        )
        if activation.scalar_one_or_none():
            return False, "Вы уже активировали этот промокод."

        # Всё ок — активируем промокод
        promo.activations += 1
        session.add(PromoActivation(user_id=user_id, promo_id=promo.id, promo_code=promo.code))

        # Применяем действие промокода
        user = await session.get(User, user_id)
        if promo.type == "discount":
            # Сохраняем скидку для применения при следующем заказе
            user.active_discount_percent = promo.value
            await session.commit()
            return True, f"Промокод активирован! Скидка {promo.value}% будет применена к вашему следующему заказу."
        elif promo.type == "bonus":
            if promo.currency == "сом":
                user.bonus_kg += promo.value
            elif promo.currency == "тенге":
                user.bonus_kz += promo.value
            elif promo.currency == "руб.":
                user.bonus_ru += promo.value
            else:
                user.bonus_ru += promo.value  # по умолчанию в рублях
            session.add(BonusHistory(
                user_id=user_id,
                amount=promo.value,
                source="Промокод",
                comment=f"Активация промокода {promo.code}"
            ))
            await session.commit()
            return True, f"Промокод активирован! Вам начислено {promo.value} {promo.currency or ''} на бонусный счёт."
        else:
            await session.commit()
            return True, "Промокод активирован!"


async def get_user_active_discount(user_id: int):
    """Получает активную скидку пользователя"""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            return user.active_discount_percent or 0
        return 0


async def apply_user_discount(user_id: int):
    """Применяет и сбрасывает активную скидку пользователя"""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user and user.active_discount_percent:
            discount = user.active_discount_percent
            user.active_discount_percent = 0  # Сбрасываем скидку после применения
            await session.commit()
            return discount
        return 0


async def get_user_bonus_balance(user_id: int, currency: str):
    """Получает бонусный баланс пользователя в указанной валюте"""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            return 0
        
        if currency == "сом":
            return user.bonus_kg or 0
        elif currency == "тенге":
            return user.bonus_kz or 0
        elif currency == "руб.":
            return user.bonus_ru or 0
        else:
            return 0


async def use_user_bonus(user_id: int, amount: float, currency: str):
    """Использует бонусы пользователя для оплаты"""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            return False, "Пользователь не найден."
        
        # Определяем поле бонуса в зависимости от валюты
        if currency == "сом":
            current_bonus = user.bonus_kg or 0
            if current_bonus < amount:
                return False, f"Недостаточно бонусов. Доступно: {current_bonus:.2f} сом"
            user.bonus_kg -= amount
        elif currency == "тенге":
            current_bonus = user.bonus_kz or 0
            if current_bonus < amount:
                return False, f"Недостаточно бонусов. Доступно: {current_bonus:.2f} тенге"
            user.bonus_kz -= amount
        elif currency == "руб.":
            current_bonus = user.bonus_ru or 0
            if current_bonus < amount:
                return False, f"Недостаточно бонусов. Доступно: {current_bonus:.2f} руб."
            user.bonus_ru -= amount
        else:
            return False, "Неподдерживаемая валюта."
        
        # Добавляем запись в историю бонусов
        session.add(BonusHistory(
            user_id=user_id,
            amount=-amount,  # Отрицательная сумма означает списание
            source="Оплата заказа",
            comment=f"Использование бонусов для оплаты заказа ({amount} {currency})"
        ))
        
        await session.commit()
        return True, f"Списано {amount:.2f} {currency} с бонусного счета."


async def delete_expired_promocodes():
    async with AsyncSessionLocal() as session:
        now_utc = datetime.now(timezone.utc)
        await session.execute(
            delete(PromoCode).where(
                PromoCode.expires_at.isnot(None),
                PromoCode.expires_at < now_utc
            )
        )
        await session.commit()

async def create_order(order_data: dict) -> Order:
    """Создает новый заказ"""
    async with AsyncSessionLocal() as session:
        # Генерируем уникальный ID заказа
        order_id = f"#Z{uuid.uuid4().hex[:6].upper()}"
        
        order = Order(
            order_id=order_id,
            user_id=order_data.get("user_id"),
            service_type=order_data.get("service_type"),
            boost_type=order_data.get("boost_type"),
            region=order_data.get("region"),
            current_rank=order_data.get("current_rank"),
            target_rank=order_data.get("target_rank"),
            current_mythic_stars=order_data.get("current_mythic_stars"),
            target_mythic_stars=order_data.get("target_mythic_stars"),
            hero=order_data.get("hero"),
            lane=order_data.get("lane"),
            heroes_mains=order_data.get("heroes_mains"),
            game_login=order_data.get("game_login"),
            game_password=order_data.get("game_password"),
            game_id=order_data.get("game_id"),
            contact_info=order_data.get("contact_info"),
            base_cost=order_data.get("base_cost"),
            multiplier=order_data.get("multiplier", 1.0),
            total_cost=order_data.get("total_cost"),
            currency=order_data.get("currency"),
            details=order_data.get("details"),
            preferred_time=order_data.get("preferred_time"),
            coaching_topic=order_data.get("coaching_topic"),
            coaching_hours=order_data.get("coaching_hours"),
            status="pending"
        )
        
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

async def get_user_orders(user_id: int, limit: int = 10, offset: int = 0):
    """Получает заказы пользователя"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

# === НОВЫЕ ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ЗАКАЗАМИ ===

async def get_order_by_id(order_id: str):
    """Получает заказ по ID"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        return result.scalar_one_or_none()

async def get_all_orders(status_filter: str = "all", limit: int = 20, offset: int = 0):
    """Получает все заказы с фильтрацией по статусу"""
    async with AsyncSessionLocal() as session:
        query = select(Order).order_by(Order.created_at.desc())
        
        if status_filter != "all":
            query = query.where(Order.status == status_filter)
        
        result = await session.execute(query.limit(limit).offset(offset))
        return result.scalars().all()

async def update_order_status(order_id: str, new_status: str):
    """Обновляет статус заказа"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = result.scalar_one_or_none()
        if order:
            order.status = new_status
            await session.commit()
            return order
        return None

async def assign_booster_to_order(order_id: str, booster_id: int):
    """Назначает бустера на заказ"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = result.scalar_one_or_none()
        if order:
            order.assigned_booster_id = booster_id
            order.status = "confirmed"
            await session.commit()
            return order
        return None

async def get_boosters():
    """Получает всех активных бустеров"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.role == "booster")
        )
        return result.scalars().all()

async def get_active_boosters():
    """Получает всех активных бустеров с их аккаунтами"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BoosterAccount)
            .join(User, BoosterAccount.user_id == User.id)
            .where(BoosterAccount.status == "active")
        )
        return result.scalars().all()

async def get_orders_by_booster(booster_id: int):
    """Получает заказы назначенные бустеру"""
    import logging
    logger = logging.getLogger(__name__)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order)
            .where(Order.assigned_booster_id == booster_id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        logger.info(f"CRUD: get_orders_by_booster({booster_id}) нашел {len(orders)} заказов")
        for order in orders[:3]:  # Логируем первые 3 заказа
            logger.info(f"CRUD: Заказ {order.order_id}: статус {order.status}, назначен {order.assigned_booster_id}")
        return orders

async def count_orders_by_status(status: str = None):
    """Подсчитывает количество заказов по статусу"""
    async with AsyncSessionLocal() as session:
        query = select(func.count()).select_from(Order)
        if status:
            query = query.where(Order.status == status)
        result = await session.execute(query)
        return result.scalar_one()

async def search_orders(query: str):
    """Поиск заказов по ID или имени пользователя"""
    async with AsyncSessionLocal() as session:
        # Поиск по ID заказа
        if query.startswith("#"):
            result = await session.execute(
                select(Order).where(Order.order_id.ilike(f"%{query}%"))
            )
            return result.scalars().all()
        
        # Поиск по имени пользователя или telegram ID
        result = await session.execute(
            select(Order)
            .join(User, Order.user_id == User.id)
            .where(
                or_(
                    User.username.ilike(f"%{query}%"),
                    User.tg_id == int(query) if query.isdigit() else False
                )
            )
        )
        return result.scalars().all()

async def update_order_price(order_id: str, new_price: float):
    """Обновляет цену заказа"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = result.scalar_one_or_none()
        if order:
            order.total_cost = new_price
            await session.commit()
            return order
        return None

async def get_orders_count(user_id: int) -> int:
    """Получает количество заказов пользователя"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order)
            .where(Order.user_id == user_id)
        )
        orders = result.scalars().all()
        return len(orders)



async def get_users_by_role(role: str):
    """Получение пользователей по роли"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.role == role)
            )
            users = result.scalars().all()
            logger.info(f"Найдено {len(users)} пользователей с ролью '{role}'")
            return users
    except Exception as e:
        logger.error(f"Ошибка получения пользователей с ролью '{role}': {e}")
        return []
