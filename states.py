from aiogram.fsm.state import State, StatesGroup


# Определение состояний профиля пользователя
class ProfileStates(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()
    calorie_goal_input = State()
    water_goal = State()
    logged_water = State()
    logged_calories = State()
    burned_calories = State()


# Состояния для тренировок
class WorkoutStates(StatesGroup):
    choose_type = State()
    choose_duration = State()