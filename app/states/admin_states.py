from aiogram.fsm.state import StatesGroup, State

class AdminStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_balance = State()