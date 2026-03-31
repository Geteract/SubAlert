from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import db
from keyboards.inline import get_main_menu
import datetime

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username
    )

    # Проверяем статус премиум
    status_text = "Бесплатный тариф (до 3 подписок)"
    if user.status.value == "premium" and user.premium_until:
        days_left = (user.premium_until - message.date).days
        if days_left > 0:
            status_text = f"💎 Премиум (осталось {days_left} дней)"

    welcome_text = (
        f"Добро пожаловать в бот для учёта подписок!\n\n"
        f"Ваш статус: {status_text}\n\n"
        f"Я помогу вам:\n"
        f"✅ Отслеживать регулярные платежи\n"
        f"✅ Получать напоминания о списаниях\n"
        f"✅ Контролировать бюджет и избегать неожиданных расходов\n\n"
        f"До 3 подписок — бесплатно!\n"
        f"Неограниченное количество — 99₽/мес\n\n"
        f"Выберите действие:"
    )

    await message.answer(welcome_text, reply_markup=get_main_menu())


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    user = await db.get_user_by_telegram_id(callback.from_user.id)

    # Проверяем статус премиум
    status_text = "Бесплатный тариф (до 3 подписок)"
    if user and user.status.value == "premium" and user.premium_until:
        days_left = (user.premium_until - datetime.now()).days
        if days_left > 0:
            status_text = f"💎 Премиум (осталось {days_left} дней)"

    welcome_text = (
        f"📱 Главное меню\n\n"
        f"Ваш статус: {status_text}\n\n"
        f"Выберите действие:"
    )

    await callback.message.edit_text(
        welcome_text,
        reply_markup=get_main_menu()
    )
    await callback.answer()