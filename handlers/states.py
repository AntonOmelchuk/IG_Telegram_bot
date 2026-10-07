from aiogram.fsm.state import State, StatesGroup


class SetupStates(StatesGroup):
    language = State()
    timezone = State()


class ProfileStates(StatesGroup):
    cp_name = State()
    nickname = State()
