from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from database import db
from utils.reminders import send_reminders, send_payment_requests

scheduler = AsyncIOScheduler()


async def setup_scheduler(bot):
    """Настройка планировщика задач"""

    # Каждый день в 10:00 проверяем напоминания
    scheduler.add_job(
        send_reminders,
        CronTrigger(hour=10, minute=0),
        args=[bot],
        id="daily_reminders"
    )

    # Каждый час проверяем платежи через диалог (за день до списания)
    scheduler.add_job(
        send_payment_requests,
        CronTrigger(minute=0),  # Каждый час
        args=[bot],
        id="payment_requests"
    )

    scheduler.start()