import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_TOKEN = os.getenv("WEATHER_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен")

if not WEATHER_TOKEN:
    raise ValueError("WEATHER_TOKEN не установлен")