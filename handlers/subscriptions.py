from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from database import db
from models import Category, Period, PaymentMethod
from keyboards.inline import (
    get_categories_keyboard, get_period_keyboard, get_payment_method_keyboard,
    get_subscription_actions, get_back_button, get_main_menu
)
from config import FREE_SUBSCRIPTION_LIMIT

router = Router()


class AddSubscriptionStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_period = State()
    waiting_for_custom_days = State()
    waiting_for_next_date = State()
    waiting_for_payment_method = State()


@router.callback_query(F.data == "add")
async def start_add_subscription(callback: CallbackQuery, state: FSMContext):
    """Начать добавление подписки"""
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)

    can_add, message = await db.can_add_subscription(user.id)
    if not can_add:
        await callback.message.edit_text(
            f"{message}\n\n"
            f"💎 Оформите премиум за 99₽/мес, чтобы добавить больше подписок",
            reply_markup=get_back_button()
        )
        await callback.answer()
        return

    await state.set_state(AddSubscriptionStates.waiting_for_name)
    await callback.message.edit_text(
        "Введите название подписки:\n\n"
        "Например: Netflix, Spotify, Страховка и т.д.",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.message(AddSubscriptionStates.waiting_for_name)
async def get_subscription_name(message: Message, state: FSMContext):
    """Получить название подписки"""
    if len(message.text) > 100:
        await message.answer("❌ Название слишком длинное (макс. 100 символов). Попробуйте снова:")
        return

    await state.update_data(name=message.text)
    await state.set_state(AddSubscriptionStates.waiting_for_amount)
    await message.answer(
        "Введите сумму подписки в рублях:\n\n"
        "Например: 499, 1000.50",
        reply_markup=get_back_button()
    )


@router.message(AddSubscriptionStates.waiting_for_amount)
async def get_subscription_amount(message: Message, state: FSMContext):
    """Получить сумму подписки"""
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
        await state.update_data(amount=amount)
        await state.set_state(AddSubscriptionStates.waiting_for_category)
        await message.answer(
            "Выберите категорию подписки:",
            reply_markup=get_categories_keyboard()
        )
    except ValueError:
        await message.answer("❌ Введите корректную сумму (положительное число). Попробуйте снова:")


@router.callback_query(AddSubscriptionStates.waiting_for_category, F.data.startswith("cat_"))
async def get_subscription_category(callback: CallbackQuery, state: FSMContext):
    """Получить категорию подписки"""
    category = callback.data.split("_")[1]
    await state.update_data(category=Category(category))
    await state.set_state(AddSubscriptionStates.waiting_for_period)
    await callback.message.edit_text(
        "Выберите периодичность списаний:",
        reply_markup=get_period_keyboard()
    )
    await callback.answer()


@router.callback_query(AddSubscriptionStates.waiting_for_period, F.data.startswith("period_"))
async def get_subscription_period(callback: CallbackQuery, state: FSMContext):
    """Получить периодичность подписки"""
    period_type = callback.data.split("_")[1]

    period_days_map = {
        "monthly": 30,
        "quarterly": 90,
        "yearly": 365
    }

    if period_type == "custom":
        await state.set_state(AddSubscriptionStates.waiting_for_custom_days)
        await callback.message.edit_text(
            "Введите количество дней между списаниями:\n\n"
            "Например: 14, 60, 180",
            reply_markup=get_back_button()
        )
        await callback.answer()
        return

    period = Period(period_type)
    await state.update_data(period=period, period_days=period_days_map[period_type])
    await state.set_state(AddSubscriptionStates.waiting_for_next_date)
    await callback.message.edit_text(
        "Введите дату первого списания в формате ДД.ММ.ГГГГ:\n\n"
        "Например: 15.03.2026",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.message(AddSubscriptionStates.waiting_for_custom_days)
async def get_custom_days(message: Message, state: FSMContext):
    """Получить кастомное количество дней"""
    try:
        days = int(message.text)
        if days <= 0:
            raise ValueError
        await state.update_data(period=Period.CUSTOM, period_days=days)
        await state.set_state(AddSubscriptionStates.waiting_for_next_date)
        await message.answer(
            "Введите дату первого списания в формате ДД.ММ.ГГГГ:",
            reply_markup=get_back_button()
        )
    except ValueError:
        await message.answer("❌ Введите корректное количество дней (положительное число). Попробуйте снова:")


@router.message(AddSubscriptionStates.waiting_for_next_date)
async def get_next_date(message: Message, state: FSMContext):
    """Получить дату следующего платежа"""
    try:
        next_date = datetime.strptime(message.text, "%d.%m.%Y")
        if next_date < datetime.now():
            await message.answer("❌ Дата не может быть в прошлом. Введите корректную дату:")
            return

        await state.update_data(next_payment_date=next_date)
        await state.set_state(AddSubscriptionStates.waiting_for_payment_method)
        await message.answer(
            "Выберите способ оплаты:",
            reply_markup=get_payment_method_keyboard()
        )
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ:")


@router.callback_query(AddSubscriptionStates.waiting_for_payment_method, F.data.startswith("payment_"))
async def get_payment_method(callback: CallbackQuery, state: FSMContext):
    """Получить способ оплаты и сохранить подписку"""
    method = callback.data.split("_")[1]
    payment_method = PaymentMethod(method)

    data = await state.get_data()
    user = await db.get_user_by_telegram_id(callback.from_user.id)

    # Сохраняем подписку
    subscription_id = await db.add_subscription(
        user_id=user.id,
        name=data['name'],
        category=data['category'],
        amount=data['amount'],
        period=data['period'],
        period_days=data['period_days'],
        next_payment_date=data['next_payment_date'],
        payment_method=payment_method
    )

    # Получаем информацию о лимите
    count = await db.get_user_subscriptions_count(user.id)
    limit_text = f"У вас {count} активных подписок"
    if user.status.value != "premium" and count >= 3:
        limit_text += " (лимит бесплатного тарифа исчерпан)"

    await callback.message.edit_text(
        f"✅ Подписка успешно добавлена!\n\n"
        f"Название: {data['name']}\n"
        f"Сумма: {data['amount']}₽\n"
        f"Категория: {data['category'].value}\n"
        f"Периодичность: {data['period'].value}\n"
        f"Первое списание: {data['next_payment_date'].strftime('%d.%m.%Y')}\n"
        f"Способ оплаты: {payment_method.value}\n\n"
        f"{limit_text}",
        reply_markup=get_back_button()
    )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "list")
async def list_subscriptions(callback: CallbackQuery):
    """Показать список подписок"""
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)

    subscriptions = await db.get_user_subscriptions(user.id)

    if not subscriptions:
        await callback.message.edit_text(
            "У вас пока нет подписок.\n\n"
            "Нажмите «Добавить», чтобы создать первую подписку.",
            reply_markup=get_back_button()
        )
        await callback.answer()
        return

    # Формируем текст со списком подписок
    text = "📋 Ваши активные подписки:\n\n"
    for i, sub in enumerate(subscriptions, 1):
        next_date = sub['next_payment_date'].strftime('%d.%m.%Y')
        text += f"{i}. *{sub['name']}*\n"
        text += f"   {sub['amount']}₽ | {sub['category']}\n"
        text += f"   Следующее списание: {next_date}\n"
        text += f"   {sub['payment_method']}\n\n"

    # Добавляем кнопки для первой подписки
    text += f"\n🔧 *Действия с подпиской «{subscriptions[0]['name']}»:*"

    await callback.message.edit_text(
        text,
        reply_markup=get_subscription_actions(subscriptions[0]['id']),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    """Вернуться к списку подписок"""
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    subscriptions = await db.get_user_subscriptions(user.id)

    if not subscriptions:
        await callback.message.edit_text(
            "У вас пока нет подписок.",
            reply_markup=get_back_button()
        )
        await callback.answer()
        return

    text = "Ваши активные подписки:\n\n"
    for i, sub in enumerate(subscriptions, 1):
        next_date = sub['next_payment_date'].strftime('%d.%m.%Y')
        text += f"{i}. *{sub['name']}*\n"
        text += f"   {sub['amount']}₽ | {sub['category']}\n"
        text += f"   Следующее списание: {next_date}\n"
        text += f"   {sub['payment_method']}\n\n"

    text += f"\n🔧 *Действия с подпиской «{subscriptions[0]['name']}»:*"

    await callback.message.edit_text(
        text,
        reply_markup=get_subscription_actions(subscriptions[0]['id']),
        parse_mode="Markdown"
    )
    await callback.answer()