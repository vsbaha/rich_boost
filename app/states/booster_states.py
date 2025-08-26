from aiogram.fsm.state import StatesGroup, State

class BoosterStates(StatesGroup):
    sending_completion_proof = State() 
    waiting_for_completion_proof = State() 
