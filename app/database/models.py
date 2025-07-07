from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    region = Column(String)
    balance = Column(Integer, default=0)         # основной баланс клиента
    bonus_balance = Column(Integer, default=0)   # бонусный баланс клиента
    role = Column(String, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BoosterAccount(Base):
    __tablename__ = "booster_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Integer, default=0)

class BoosterPayout(Base):
    __tablename__ = "booster_payouts"
    id = Column(Integer, primary_key=True)
    booster_account_id = Column(Integer, ForeignKey("booster_accounts.id"))
    amount = Column(Integer)
    paid_at = Column(DateTime(timezone=True), server_default=func.now())
    comment = Column(String)