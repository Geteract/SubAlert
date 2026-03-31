import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import db
from handlers import start, subscriptions, payments, forecast, premium
from utils.scheduler import setup_scheduler

# Настройка логирования
logging.basicConfig(level=logging.INFO)


async def main():
    """Главная функция запуска бота"""

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация базы данных
    await db.init()
    logging.info("База данных инициализирована")

    # Подключение роутеров
    dp.include_router(start.router)
    dp.include_router(subscriptions.router)
    dp.include_router(payments.router)
    dp.include_router(forecast.router)
    dp.include_router(premium.router)

    # Запуск планировщика
    await setup_scheduler(bot)
    logging.info("Планировщик запущен")

    # Запуск бота
    logging.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())