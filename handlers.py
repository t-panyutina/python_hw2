from aiogram.types import ReplyKeyboardRemove, CallbackQuery
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from states import ProfileStates, WorkoutStates
from aiogram.fsm.context import FSMContext
from aiogram import Router
import requests
from config import WEATHER_TOKEN

router = Router()

users = {}
users_data = {}

WORKOUT_TYPES = ["Кардио", "Силовая", "Бытовые дела", "Сидячая работа"]
CALORIES_PER_MINUTE = {"Кардио": 10, "Силовая": 8, "Бытовые дела": 4, "Сидячая работа": 3}
WATER_PER_MINUTE = {"Кардио": 8, "Силовая": 6, "Бытовые дела": 4, "Сидячая работа": 1}


def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products: 
            first_product = products[0]
            return {
                'name': first_product.get('product_name', 'Неизвестно'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
        return None
    print(f"Ошибка: {response.status_code}")
    return None


def calculate_water_norm(weight, activity):
    base_water = weight * 35 
    activ_water = activity * 500 / 60
    return round(base_water + activ_water, 1)


def calculate_calories_norm(weight, height, age, activity):
    clrs = 10 * weight + 6.25 * height - 5 * age + 5
    return round(clrs * activity / 60, 1)


def get_temp(city, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        weather_data = response.json()
        curr_temp = weather_data['main']['temp']
        return curr_temp
    else:
        return 20
    

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(
        "Привет!\nВведи /set_profile, чтобы начать.")


@router.message(Command('set_profile'))
async def set_profile(message: Message, state: FSMContext):
    await state.set_state(ProfileStates.weight)
    await message.answer("Введи вес (в кг):")


@router.message(ProfileStates.weight)
async def get_weight(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer('Введи число')
        return
    await state.update_data(weight=int(message.text))
    await state.set_state(ProfileStates.height)
    await message.answer("Введи рост (в см):")


@router.message(ProfileStates.height)
async def get_height(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer('Введи число')
        return
    await state.update_data(height=int(message.text))
    await state.set_state(ProfileStates.age)
    await message.answer("Введи возраст:")


@router.message(ProfileStates.age)
async def get_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer('Введи число.')
        return
    await state.update_data(age=int(message.text))
    await state.set_state(ProfileStates.activity)
    await message.answer("Активность за день в минутах")


@router.message(ProfileStates.activity)
async def get_activity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введи число")
        return
    await state.update_data(activity=int(message.text))
    await state.set_state(ProfileStates.city)
    await message.answer("В каком ты городе? (Укажи на английском)")


@router.message(ProfileStates.city)
async def get_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(ProfileStates.calorie_goal_input)
    await message.answer("Цель по количеству калорий?\n"
                         "Укажи ее (в ккал). Если нет, введи 'нет'")


@router.message(ProfileStates.calorie_goal_input)
async def get_calorie_input(message: Message, state: FSMContext):
    user_answer = message.text.strip().lower()
    user_data = await state.get_data()
    if user_answer == 'нет':
        calorie_goal = calculate_calories_norm(
            weight=user_data['weight'],
            height=user_data['height'],
            age=user_data['age'],
            activity=user_data['activity'])
        await state.update_data(calorie_goal=calorie_goal)

    elif user_answer.isdigit():
        calorie_goal = int(user_answer)
        await state.update_data(calorie_goal=calorie_goal)

    else:
        await message.answer("Введи число или слово 'нет'")
        return

    water_goal = calculate_water_norm(
        weight=user_data['weight'],
        activity=user_data['activity'])

    current_temp = get_temp(user_data['city'], WEATHER_TOKEN)
    if current_temp > 25:
        water_goal += 500
    await state.update_data(water_goal=water_goal)

    user_data = await state.get_data()

    user_id = message.from_user.id
    users_data[user_id] = {
        "weight": user_data['weight'],
        "height": user_data['height'],
        "age": user_data['age'],
        "activity": user_data['activity'],
        "city": user_data['city'],
        "calorie_goal": calorie_goal,
        "water_goal": water_goal}

    await message.answer(
        f"Ваш профиль сохранен:\n"
        f"Вес: {user_data['weight']} кг\n"
        f"Рост: {user_data['height']} см\n"
        f"Возраст: {user_data['age']} лет\n"
        f"Активность за день: {user_data['activity']} минут\n"
        f"Город: {user_data['city']}\n"
        f"Цель по воде: {water_goal} мл\n"
        f"Цель по калориям: {calorie_goal} ккал",
        reply_markup=ReplyKeyboardRemove())
    await state.clear()


@router.message(Command('show_profile'))
async def show_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in users_data:
        await message.answer("Профиль не найден. Сначала настрой профиль с помощью /set_profile")
        return

    user_profile = users_data[user_id]

    profile_info = (
        f"Твой профиль\n\n"  
        f"Рост: {user_profile.get('height', 'не указан')} см\n"
        f"Возраст: {user_profile.get('age', 'не указан')} лет\n"
        f"Вес: {user_profile.get('weight', 'не указан')} кг\n"
        f"Цель по калориям: {user_profile.get('calorie_goal', 'не указана')} ккал\n"
        f"Цель по воде: {user_profile.get('water_goal', 'не указана')} мл\n"
        f"Активность за день: {user_profile.get('activity', 'не указана')} мин/день\n"
        f"Город: {user_profile.get('city', 'не указан')}\n"
    )

    logged_info = (
        f"\nЗалогированные показатели:\n"
        f"Выпито: {user_profile.get('logged_water', 0)} мл\n"
        f"Потреблено: {user_profile.get('logged_calories', 0)} ккал\n"
        f"Сожжено: {user_profile.get('burned_calories', 0)} ккал\n")

    await message.answer(profile_info + logged_info)


@router.message(Command('log_water'))
async def log_water(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in users_data or "water_goal" not in users_data[user_id]:
        await message.answer("Профиль не найден. Сначала настрой профиль с помощью /set_profile.")
        return

    await state.set_state(ProfileStates.logged_water)
    await message.answer("Сколько воды (в мл) вы выпили за день?")


@router.message(ProfileStates.logged_water)
async def handle_logged_water(message: Message, state: FSMContext):
    user_answer = message.text.strip().lower()
    if user_answer.isdigit():

        logged_water = int(user_answer)
        await state.update_data(logged_water=logged_water)

        user_id = message.from_user.id
        if "logged_water" not in users_data[user_id]:
            users_data[user_id]["logged_water"] = 0 
        users_data[user_id]["logged_water"] += logged_water
        logged_water = users_data[user_id]["logged_water"]

        water_goal = users_data[user_id]["water_goal"]
        water_left = round(water_goal - logged_water)

        if water_left <= 0:
            await message.answer(f"Вы выпили дневную норму воды")
        else:
            await message.answer(f"Вы выпили {logged_water} мл воды\n"
                                 f"До выполнения нормы осталось выпить {water_left} мл.")
        await state.clear()
    else:
        await message.answer("Введи число")


@router.message(Command('log_food'))
async def log_food(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users_data:
        await message.answer("Профиль не найден. Сначала настрой профиль с помощью /set_profile")
        return

    await state.set_state(ProfileStates.logged_calories)
    await message.answer("Введи продукт и вес в граммах через пробел")


@router.message(ProfileStates.logged_calories)
async def handle_logged_calories(message: Message, state: FSMContext):
    user_answer = message.text.strip().lower().split(' ')
    user_clrs = user_answer[-1]
    user_food = user_answer[0]
    if user_clrs.isdigit():
        
        food_info = get_food_info(user_food)
        if food_info is None:
            food_clrs = {'calories': 250}.get('calories') #если апи не отвечает
        else:
            food_clrs = food_info.get('calories')

        logged_calories = (int(user_clrs) * food_clrs) / 100
        await state.update_data(logged_calories=logged_calories)

        user_id = message.from_user.id
        if "logged_calories" not in users_data[user_id]:
            users_data[user_id]["logged_calories"] = 0
        users_data[user_id]["logged_calories"] += logged_calories

        await message.answer(f"{user_food} - {food_clrs} ккал на 100 г\n"
                             f"Записано {logged_calories} ккал")
        await state.clear()
    else:
        await message.answer("Введи число")


@router.message(Command('log_workout'))
async def log_workout(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users_data:
        await message.answer("Профиль не найден. Сначала настрой профиль с помощью /set_profile.")
        return

    # Инлайн-клавиатура с типами тренировок
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=workout, callback_data=f"workout_type:{workout}")]
        for workout in WORKOUT_TYPES])

    await message.answer("Выбери тип активности:", reply_markup=keyboard)
    await state.set_state(WorkoutStates.choose_type)


# Обработчик выбора типа тренировки
@router.callback_query(lambda c: c.data.startswith("workout_type"))
async def choose_type(callback_query: CallbackQuery, state: FSMContext):
    workout_type = callback_query.data.split(":")[1]
    await state.update_data(workout_type=workout_type)
    await callback_query.message.edit_text(f"Тренировка: {workout_type}")

    durations = ["15 минут", "30 минут", "45 минут", "60 минут", "75 минут", "90 минут"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=duration, callback_data=f"workout_duration:{duration}")]
        for duration in durations])
    await callback_query.message.answer("Теперь выбери длительность тренировки:", reply_markup=keyboard)
    await state.set_state(WorkoutStates.choose_duration)


@router.callback_query(lambda c: c.data.startswith("workout_duration"))
async def choose_duration(callback_query: CallbackQuery, state: FSMContext):
    duration = callback_query.data.split(":")[1]
    duration_mins = int(duration.split()[0])
    user_data = await state.get_data()
    workout_type = user_data.get("workout_type")

    burned_calories = CALORIES_PER_MINUTE.get(workout_type, 0) * duration_mins
    extra_water = WATER_PER_MINUTE.get(workout_type, 0) * duration_mins
    await state.update_data(burned_calories=burned_calories)

    user_id = callback_query.from_user.id
    if "burned_calories" not in users_data[user_id]:
        users_data[user_id]["burned_calories"] = 0
    users_data[user_id]["burned_calories"] += burned_calories
    users_data[user_id]["water_goal"] += extra_water

    calorie_goal = users_data[user_id]["calorie_goal"]
    logged_calories = users_data[user_id]['logged_calories']
    balance_calories = round(logged_calories - burned_calories)

    result_text = (
        f"Тренировка: {workout_type}, длительность: {duration}\n"
        f"Сожжено: {burned_calories} ккал\n"
        f"Рекомендуется выпить дополнительно: {extra_water} мл\n")

    burned_calories = users_data[user_id]["burned_calories"]
    balance_calories = round(logged_calories - burned_calories)
    if balance_calories <= calorie_goal:
        result_text += "Баланс по калориям"
    else:
        result_text += (
            f"Необходимо сжечь не менее {balance_calories - calorie_goal} ккал\n")

    await callback_query.message.edit_text(result_text)
    await state.clear()


@router.message(Command('check_progress'))
async def check_progress(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users_data:
        await message.answer("Профиль не найден. Сначала настрой профиль с помощью /set_profile.")
        return

    required_keys = {
        'logged_water': "Информация о выпитой воде не найдена\nСначала запиши её с помощью /log_water.",
        'logged_calories': "Информация о потребленных калорий\ях не найдена\nСначала запиши ее с помощью /log_food.",
        'burned_calories': "Информация о сожжённых калориях не найдена\nСначала запиши ее с помощью /log_workout."}

    for key, error_message in required_keys.items():
        if key not in users_data[user_id]:
            await message.answer(error_message)
            return

    logged_water = users_data[user_id]['logged_water']
    water_goal = users_data[user_id]['water_goal']
    if round(water_goal - logged_water) <= 0:
        water_left = 0
    else:
        water_left = round(water_goal - logged_water)

    logged_calories = users_data[user_id]['logged_calories']
    calorie_goal = users_data[user_id]['calorie_goal']
    burned_calories = users_data[user_id]['burned_calories']
    balance_calories = round(logged_calories - burned_calories)

    result_text = ("Твой прогресс:\nВода:\n"
                   f"- Осталось воды: {water_left} мл.\n\nКалории:\n"
                   f"- Выпито: {logged_water} мл из {water_goal} мл.\n"
                   f"- Сожжено: {burned_calories} ккал.\n"
                   f"- Потреблено: {logged_calories} ккал. из {calorie_goal} ккал.\n"
                   f"- Баланс калорий: {balance_calories}\n")

    if balance_calories <= calorie_goal:
        result_text += "Баланс по калориям"
    elif balance_calories > calorie_goal:
        result_text += (
            f"Необходимо сжечь не менее {balance_calories - calorie_goal} ккал\n")
    elif water_left <= 0:
        result_text += ("Вы выпили дневную норму")
    elif water_left > 0:
        result_text += (f"До выполнения нормы {water_left} мл")
    elif balance_calories > calorie_goal and water_left > 0:
        result_text += (
            f"Необходимо сжечь не менее {balance_calories - calorie_goal} ккал\n"
            f"До выполнения нормы осталось {water_left} мл\n")

    await message.answer(result_text)
    await state.clear()

def setup_handlers(dp):
    dp.include_router(router)