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
from app.database.models import User, BonusHistory, PromoCode, PromoActivation, Order

bot = Bot(token=BOT_TOKEN)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

async def get_booster_account(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BoosterAccount).where(BoosterAccount.user_id == user_id))
        return result.scalar_one_or_none()

async def create_booster_account(user_id, username, session):
    from app.database.models import BoosterAccount
    account = BoosterAccount(user_id=user_id, username=username)
    session.add(account)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()

async def update_booster_balance(user_id, amount):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BoosterAccount).where(BoosterAccount.user_id == user_id))
        account = result.scalar_one_or_none()
        if account:
            account.balance += amount
            await session.commit()

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

async def update_user_balance(tg_id, new_balance):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            if user.region == "🇰🇬 КР":
                user.balance_kg = new_balance
            elif user.region == "🇰🇿 КЗ":
                user.balance_kz = new_balance
            elif user.region == "🇷🇺 РУ":
                user.balance_ru = new_balance
            await session.commit()

async def update_user_bonus_balance(tg_id, new_bonus_balance):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            if user.region == "🇰🇬 КР":
                user.bonus_kg = new_bonus_balance
            elif user.region == "🇰🇿 КЗ":
                user.bonus_kz = new_bonus_balance
            elif user.region == "🇷🇺 РУ":
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

async def update_user_balance_by_region(user, region, amount):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user.id))
        user_db = result.scalar_one_or_none()
        if user_db:
            is_first_topup = (
                user_db.balance_kg == 0 and
                user_db.balance_kz == 0 and
                user_db.balance_ru == 0
            )
            # Пополняем баланс
            if region == "🇰🇬 КР":
                user_db.balance_kg += amount
            elif region == "🇰🇿 КЗ":
                user_db.balance_kz += amount
            elif region == "🇷🇺 РУ":
                user_db.balance_ru += amount
            await session.commit()

            # Если это первое пополнение — начисляем бонус пригласившему
            if is_first_topup and user_db.referrer_id:
                BONUS_AMOUNT = 50  # укажи нужную сумму
                await add_bonus_to_referrer(user_db.id, BONUS_AMOUNT)

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
        if promo.expires_at and promo.expires_at < datetime.now(timezone.utc):
            return False, "Срок действия промокода истёк."

        # Проверка лимита активаций
        if promo.max_activations is not None and promo.activations >= promo.max_activations:
            return False, "Лимит активаций промокода исчерпан."

        # Проверка на повторную активацию (для всех промокодов)
        activation = await session.execute(
            select(PromoActivation).where(
                PromoActivation.user_id == user_id,
                PromoActivation.promo_id == promo.id
            )
        )
        if activation.scalar_one_or_none():
            return False, "Вы уже активировали этот промокод."

        # Всё ок — активируем промокод
        promo.activations += 1
        session.add(PromoActivation(user_id=user_id, promo_id=promo.id))

        # Применяем действие промокода
        user = await session.get(User, user_id)
        if promo.type == "discount":
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

async def get_order_by_id(order_id: str):
    """Получает заказ по ID"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order)
            .where(Order.order_id == order_id)
        )
        return result.scalar_one_or_none()

async def update_order_status(order_id: str, new_status: str):
    """Обновляет статус заказа"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order)
            .where(Order.order_id == order_id)
        )
        order = result.scalar_one_or_none()
        if order:
            order.status = new_status
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
