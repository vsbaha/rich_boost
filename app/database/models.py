from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Float, Boolean, Text

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
    type = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    currency = Column(String, nullable=True)
    is_one_time = Column(Boolean, default=True) 
    max_activations = Column(Integer, nullable=True) 
    activations = Column(Integer, default=0)  
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True) 
    comment = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)  # Новое поле

class PromoActivation(Base):
    __tablename__ = "promo_activations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    promo_id = Column(Integer)
    activated_at = Column(DateTime(timezone=True), server_default=func.now())

class BonusHistory(Base):
    __tablename__ = "bonus_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    source = Column(String)  # например: "Реферал", "Промокод", "Админ"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    comment = Column(String, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)  # Уникальный ID заказа (#Z1234)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Основная информация
    service_type = Column(String)  # "regular_boost", "hero_boost", "coaching"
    boost_type = Column(String)    # "account", "shared", "mmr", "winrate", "coaching"
    
    # Игровые данные
    region = Column(String)
    current_rank = Column(String)
    target_rank = Column(String)
    current_mythic_stars = Column(Integer, nullable=True)
    target_mythic_stars = Column(Integer, nullable=True)
    hero = Column(String, nullable=True)
    lane = Column(String, nullable=True)
    heroes_mains = Column(String, nullable=True)
    
    # Аккаунт данные
    game_login = Column(String, nullable=True)
    game_password = Column(String, nullable=True)
    game_id = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    
    # Финансы
    base_cost = Column(Float)
    multiplier = Column(Float, default=1.0)
    total_cost = Column(Float)
    currency = Column(String)
    
    # Дополнительная информация
    details = Column(Text, nullable=True)
    preferred_time = Column(String, nullable=True)
    coaching_topic = Column(String, nullable=True)
    coaching_hours = Column(Integer, nullable=True)
    
    # Статус заказа
    status = Column(String, default="pending")  # pending, confirmed, in_progress, completed, cancelled
    
    # Даты
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    assigned_booster_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    def __repr__(self):
        return f"<Order {self.order_id}>"

