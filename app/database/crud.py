from .db import AsyncSessionLocal
from .models import User, Base
from sqlalchemy.future import select

async def init_db():
    async with AsyncSessionLocal() as session:
        async with session.bind.begin() as conn:
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