from aiogram.fsm.state import StatesGroup, State

class AdminStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_balance = State()
    waiting_for_bonus = State()
    waiting_for_broadcast = State()
    waiting_for_boosters_broadcast = State()
    
class SearchStates(StatesGroup):
    waiting_for_id = State()
    
class PromoCreateStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_type = State()
    waiting_for_value = State()
    waiting_for_currency = State()
    waiting_for_one_time = State()
    waiting_for_max_activations = State()
    waiting_for_expires = State()
    waiting_for_comment = State()
    waiting_for_search = State()
    confirm = State()

class PromoEditStates(StatesGroup):
    choosing_field = State()
    editing_code = State()
    editing_type = State()
    editing_value = State()
    editing_currency = State()
    editing_max_activations = State()
    editing_expires = State()
    editing_comment = State()