from aiogram.fsm.state import StatesGroup, State

class RegionStates(StatesGroup):
    waiting_for_region = State()