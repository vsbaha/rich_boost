from .db import AsyncSessionLocal
from .models import User, Base, BoosterAccount, PaymentRequest
from sqlalchemy.future import select
from .models import Base
from .db import engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from datetime import datetime, timezone
from aiogram import Bot
from app.config import BOT_TOKEN
from app.database.models import User, BonusHistory

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
                            f"Вам начислен бонус {amount} за первое пополнение приглашённого друга!"
                        )
                    except Exception:
                        pass  # если пользователь заблокировал бота и т.д.
