import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import setup_handlers
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares import LoggingMiddleware

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(LoggingMiddleware())
setup_handlers(dp)


async def set_bot_commands(bot: Bot):
    commands = [
        {"command": "start", "description": "Начать работу с ботом"},
        {"command": "set_profile", "description": "Настроить профиль"},
        {"command": "show_profile", "description": "Просмотр текущего профиля"},
        {"command": "log_water", "description": "Количество выпитой воды"},
        {"command": "log_food", "description": "Количество ккал"},
        {"command": "log_workout", "description": "Количество сожженных калорий на тренировке"},
        {"command": "check_progress", "description": "Прогресс по воде и калориям"}
    ]
    await bot.set_my_commands(commands)


async def main():
    await set_bot_commands(bot)

    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())