from .db import AsyncSessionLocal
from .models import User, Base, BoosterAccount
from sqlalchemy.future import select
from .models import Base
from .db import engine
from sqlalchemy import func, or_

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def add_user(tg_id, username, region=None, role="user"):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(tg_id=tg_id, username=username, region=region, role=role)
            session.add(user)
            await session.commit()

async def update_user_region(tg_id, region):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.region = region
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

async def create_booster_account(user_id):
    async with AsyncSessionLocal() as session:
        account = BoosterAccount(user_id=user_id)
        session.add(account)
        await session.commit()
        return account

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
            user.balance = new_balance
            await session.commit()