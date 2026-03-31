from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta
from database import db
from keyboards.inline import get_back_button, get_premium_keyboard
from config import PREMIUM_PRICE

router = Router()


@router.callback_query(F.data == "premium")
async def show_premium_info(callback: CallbackQuery):
    """Показать информацию о премиум"""
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)

    text = "💎 **Премиум подписка**\n\n"
    text += "**Что дает премиум:**\n"
    text += "✅ Неограниченное количество подписок\n"
    text += "✅ Расширенная аналитика\n"
    text += "✅ Приоритетная поддержка\n"
    text += "✅ Экспорт данных\n\n"

    text += f" **Стоимость:** {PREMIUM_PRICE}₽/мес\n\n"

    if user.status.value == "premium" and user.premium_until:
        days_left = (user.premium_until - datetime.now()).days
        if days_left > 0:
            text += f"✨ **Ваш статус:** Активен (осталось {days_left} дней)"
        else:
            text += "⚠ **Ваш премиум истек!** Продлите, чтобы продолжить пользоваться преимуществами."
    else:
        count = await db.get_user_subscriptions_count(user.id)
        text += f" У вас {count} из 3 бесплатных подписок\n\n"
        text += " **Оформите премиум, чтобы добавить больше подписок!**"

    await callback.message.edit_text(
        text,
        reply_markup=get_premium_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    """Купить премиум (демо-версия с бесплатным получением)"""
    # В реальном проекте здесь была бы интеграция с платежной системой
    # Для демо просто активируем премиум на 30 дней

    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)

    valid_until = datetime.now() + timedelta(days=30)
    await db.add_premium_transaction(user.id, PREMIUM_PRICE, valid_until)

    await callback.message.edit_text(
        f"🎉 **Поздравляем!**\n\n"
        f"Премиум подписка активирована на 30 дней!\n\n"
        f"📅 Действует до: {valid_until.strftime('%d.%m.%Y')}\n\n"
        f"Теперь вы можете добавить неограниченное количество подписок.",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    await callback.answer("Премиум активирован! 🎉")