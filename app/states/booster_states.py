from aiogram.fsm.state import StatesGroup, State

class BoosterStates(StatesGroup):
    sending_completion_proof = State()  # Отправка скриншота завершения заказа
    waiting_for_completion_proof = State()  # Ожидание скриншота завершения
