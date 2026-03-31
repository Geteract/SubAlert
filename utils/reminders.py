from datetime import datetime, timedelta
from database import db
from keyboards.inline import get_confirm_payment_keyboard


async def send_reminders(bot):
    """Отправить напоминания о предстоящих платежах"""
    # Получаем все активные подписки
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT s.*, u.telegram_id FROM subscriptions s "
            "JOIN users u ON s.user_id = u.id "
            "WHERE s.status = 'active' "
            "AND s.next_payment_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '3 days'"
        )

        for row in rows:
            days_left = (row['next_payment_date'] - datetime.now().date()).days

            if days_left == 3:
                text = f"🔔 **Напоминание!**\n\n"
                text += f"Через 3 дня списание по подписке **{row['name']}**\n"
                text += f"💰 Сумма: {row['amount']}₽\n"
                text += f"📅 Дата: {row['next_payment_date'].strftime('%d.%m.%Y')}"

                await bot.send_message(
                    chat_id=row['telegram_id'],
                    text=text,
                    parse_mode="Markdown"
                )

            elif days_left == 1 and row['payment_method'] == 'dialog':
                text = f"🔔 **Скоро списание!**\n\n"
                text += f"Подписка: **{row['name']}**\n"
                text += f"💰 Сумма: {row['amount']}₽\n\n"
                text += f"Подтвердите списание:"

                await bot.send_message(
                    chat_id=row['telegram_id'],
                    text=text,
                    reply_markup=get_confirm_payment_keyboard(row['id']),
                    parse_mode="Markdown"
                )


async def send_payment_requests(bot):
    """Отправить запросы на подтверждение платежей"""
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT s.*, u.telegram_id FROM subscriptions s "
            "JOIN users u ON s.user_id = u.id "
            "WHERE s.status = 'active' "
            "AND s.payment_method = 'dialog' "
            "AND s.next_payment_date = CURRENT_DATE + INTERVAL '1 day'"
        )

        for row in rows:
            text = f"💳 **Запрос на списание**\n\n"
            text += f"Завтра будет списание по подписке **{row['name']}**\n"
            text += f"💰 Сумма: {row['amount']}₽\n\n"
            text += f"Подтвердите списание или отложите:"

            await bot.send_message(
                chat_id=row['telegram_id'],
                text=text,
                reply_markup=get_confirm_payment_keyboard(row['id']),
                parse_mode="Markdown"
            )