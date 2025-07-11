from aiogram.fsm.state import StatesGroup, State

class RegionStates(StatesGroup):
    waiting_for_region = State()
    
class TopUpStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()