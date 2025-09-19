from aiogram.fsm.state import StatesGroup, State

class BoosterStates(StatesGroup):
    sending_completion_proof = State() 
    waiting_for_completion_proof = State()
    collecting_completion_files = State()  # Новое состояние для сбора множественных файлов
    waiting_for_more_files = State()       # Состояние ожидания добавления еще файлов
    entering_convert_amount = State() 
    
    # Payout request states
    selecting_payout_currency = State()
    entering_payout_amount = State()
    entering_payment_details = State()  # Ввод реквизитов
    confirming_payout_request = State() 
