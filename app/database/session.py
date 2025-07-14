from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from .db import engine

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

def get_session() -> AsyncSession:
    return AsyncSessionLocal()