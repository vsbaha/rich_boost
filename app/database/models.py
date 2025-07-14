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
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # <-- Новое поле

class BoosterAccount(Base):
    __tablename__ = "booster_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    username = Column(String) 
    balance = Column(Float, default=0)
    status = Column(String, default="active") 

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

class PromoCode(Base):
    __tablename__ = "promo_codes"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # "discount" или "amount"
    value = Column(Float, nullable=False)  # % или сумма
    max_activations = Column(Integer, nullable=True)  # None = бесконечно
    activations = Column(Integer, default=0)
    is_active = Column(Integer, default=1)

class PromoActivation(Base):
    __tablename__ = "promo_activations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    promo_id = Column(Integer, ForeignKey("promo_codes.id"))
    activated_at = Column(DateTime(timezone=True), server_default=func.now())

class BonusHistory(Base):
    __tablename__ = "bonus_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    source = Column(String)  # например: "Реферал", "Промокод", "Админ"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    comment = Column(String, nullable=True)

