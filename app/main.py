from fastapi import FastAPI
from app.api import auth, bookings, users, courts, profile
from app.db.base import Base
from app.db.session import engine
from dotenv import load_dotenv
import os

# Загружаем переменные окружения из .env
load_dotenv()

# Проверяем наличие API-ключа P1SMS
SMS_P1SMS_API_KEY = os.getenv("SMS_P1SMS_API_KEY")
if not SMS_P1SMS_API_KEY:
    raise ValueError("SMS_P1SMS_API_KEY not found in environment variables")

app = FastAPI(title="Tennis Project API")

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

# Подключаем роутеры
app.include_router(auth.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(courts.router, prefix="/api")
app.include_router(profile.router, prefix="/api")