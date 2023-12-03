from aiogram.fsm.state import StatesGroup, State


class PossibleStates(StatesGroup):
    start = State()
    tranlog = State()
    open = State()
