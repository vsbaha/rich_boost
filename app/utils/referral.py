from app.database.models import User
from sqlalchemy.future import select
from app.database.db import AsyncSessionLocal

async def get_referrals_count(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.referrer_id == user_id))
        return result.scalars().all()

def get_referral_link(user):
    return f"https://t.me/Rich_boostBot?start=ref{user.id}"  # Используй user.id!