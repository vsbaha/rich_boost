from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Float

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String)
    region = Column(String)
    balance_kg = Column(Float, default=0)
    balance_kz = Column(Float, default=0)
    balance_ru = Column(Float, default=0)
    bonus_kg = Column(Float, default=0)
    bonus_kz = Column(Float, default=0)
    bonus_ru = Column(Float, default=0)
    role = Column(String, default="user", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BoosterAccount(Base):
    __tablename__ = "booster_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Float, default=0)         

class BoosterPayout(Base):
    __tablename__ = "booster_payouts"
    id = Column(Integer, primary_key=True)
    booster_account_id = Column(Integer, ForeignKey("booster_accounts.id"))
    amount = Column(Float)                     
    paid_at = Column(DateTime(timezone=True), server_default=func.now())
    comment = Column(String)

class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    region = Column(String)
    amount = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")  # pending, accepted, rejected
    receipt_file_id = Column(String)  # file_id скрина чека