from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta
from database import db
from keyboards.inline import get_back_button

router = Router()


@router.callback_query(F.data == "forecast")
async def show_forecast(callback: CallbackQuery):
    """Показать прогноз расходов"""
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)

    forecast = await db.get_forecast(user.id)

    if forecast['subscriptions_count'] == 0:
        await callback.message.edit_text(
            "У вас пока нет подписок для прогноза.\n\n"
            "Добавьте первую подписку, чтобы увидеть прогноз расходов.",
            reply_markup=get_back_button()
        )
        await callback.answer()
        return

    text = "**Прогноз расходов**\n\n"

    # Общая сумма
    text += f"**Всего в месяц:** {forecast['total_monthly']:.2f}₽\n\n"

    # По категориям
    text += "**По категориям:**\n"
    for category, amount in forecast['by_category'].items():
        text += f"   • {category}: {amount:.2f}₽\n"

    # Ближайшие списания
    text += "\n **Ближайшие списания (30 дней):**\n"
    if forecast['upcoming']:
        for sub in forecast['upcoming'][:10]:  # Показываем максимум 10
            date = sub['next_payment_date'].strftime('%d.%m')
            text += f"   • {date} — {sub['name']}: {sub['amount']}₽\n"
    else:
        text += "   • Нет списаний в ближайшие 30 дней\n"

    # Предупреждение о лимите
    if user.status.value != "premium" and forecast['subscriptions_count'] >= 3:
        text += "\n️ **Внимание!**\n"
        text += "У вас активны 3 подписки (максимум для бесплатного тарифа).\n"
        text += "Оформите премиум за 99₽/мес для добавления новых подписок."

    await callback.message.edit_text(
        text,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()