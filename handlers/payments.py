from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime
from database import db
from keyboards.inline import get_subscription_actions, get_back_button

router = Router()


@router.callback_query(F.data.startswith("pay_"))
async def mark_payment(callback: CallbackQuery):
    """Отметить платеж вручную"""
    subscription_id = int(callback.data.split("_")[1])
    subscription = await db.get_subscription(subscription_id)

    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return

    # Записываем платеж
    await db.record_payment(subscription_id, subscription['amount'])

    await callback.message.edit_text(
        f"✅ Платеж по подписке «{subscription['name']}» на сумму {subscription['amount']}₽ успешно отмечен!\n\n"
        f"Следующее списание: {(datetime.now() + __import__('datetime').timedelta(days=subscription['period_days'])).strftime('%d.%m.%Y')}",
        reply_markup=get_back_button()
    )
    await callback.answer("Платеж отмечен ✅")


@router.callback_query(F.data.startswith("pause_"))
async def pause_subscription(callback: CallbackQuery):
    """Приостановить подписку"""
    subscription_id = int(callback.data.split("_")[1])
    subscription = await db.get_subscription(subscription_id)

    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return

    await db.update_subscription(subscription_id, status="paused")

    await callback.message.edit_text(
        f"⏸ Подписка «{subscription['name']}» приостановлена.\n\n"
        f"Напоминания и учет платежей временно отключены.",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_"))
async def delete_subscription(callback: CallbackQuery):
    """Удалить подписку"""
    subscription_id = int(callback.data.split("_")[1])
    subscription = await db.get_subscription(subscription_id)

    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return

    await db.delete_subscription(subscription_id)

    await callback.message.edit_text(
        f"❌ Подписка «{subscription['name']}» удалена.",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_payment(callback: CallbackQuery):
    """Подтвердить автоматический платеж"""
    subscription_id = int(callback.data.split("_")[2])
    subscription = await db.get_subscription(subscription_id)

    if not subscription:
        await callback.answer("Подписка не найдена", show_alert=True)
        return

    # Записываем платеж
    await db.record_payment(subscription_id, subscription['amount'])

    await callback.message.edit_text(
        f"✅ Списание по подписке «{subscription['name']}» на сумму {subscription['amount']}₽ подтверждено!",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delay_pay_"))
async def delay_payment(callback: CallbackQuery):
    """Отложить платеж"""
    subscription_id = int(callback.data.split("_")[2])
    subscription = await db.get_subscription(subscription_id)

    await callback.message.edit_text(
        f"⏸ Платеж по подписке «{subscription['name']}» отложен.\n\n"
        f"Напоминание придет через 24 часа.",
        reply_markup=get_back_button()
    )
    await callback.answer()