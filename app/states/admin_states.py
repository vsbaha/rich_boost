from aiogram.fsm.state import StatesGroup, State

class AdminStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_balance = State()
    waiting_for_bonus = State()
    waiting_for_broadcast = State()
    waiting_for_boosters_broadcast = State()