from aiogram.fsm.state import StatesGroup, State

class RegionStates(StatesGroup):
    waiting_for_region = State()
    
class TopUpStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()
    
class PromoStates(StatesGroup):
    waiting_for_promo_code = State()

# Добавляем состояния для заказов
class OrderStates(StatesGroup):
    # Основные этапы
    choosing_service = State()          # Выбор типа услуги
    choosing_boost_type = State()       # Выбор типа буста
    
    # Новая система выбора рангов
    choosing_main_rank = State()        # Выбор основного ранга (Warrior, Epic, Legend)
    choosing_rank_gradation = State()   # Выбор градации ранга (Legend I, Legend II)
    choosing_target_main_rank = State() # Выбор основного целевого ранга
    choosing_target_gradation = State() # Выбор градации целевого ранга
    
    # Mythic звезды
    entering_current_mythic = State()   # Ввод текущих звезд Mythic
    entering_target_mythic = State()    # Ввод желаемых звезд Mythic
    
    # Данные для буста
    entering_account_data = State()     # Ввод данных аккаунта (deprecated)
    entering_game_login = State()       # Ввод логина аккаунта
    entering_game_password = State()    # Ввод пароля аккаунта
    entering_game_id = State()          # Ввод игрового ID
    choosing_lane = State()             # Выбор лайна
    entering_heroes = State()           # Ввод мейнов
    entering_preferred_time = State()   # Ввод удобного времени
    
    # Обучение
    entering_coaching_hours = State()   # Количество часов обучения
    entering_coaching_topic = State()   # Тема обучения
    entering_contact_info = State()     # Контакты для обучения
    
    # Финальные этапы
    entering_details = State()          # Дополнительные детали
    confirming_order = State()          # Подтверждение заказа
    editing_order = State()             # Редактирование заказа
    
    # Оплата заказа
    payment_selection = State()         # Выбор способа оплаты (баланс/бонусы)
    bonus_amount_input = State()        # Ввод суммы бонусов к использованию