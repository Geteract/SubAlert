from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models import Category, PaymentMethod

def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=" Мои подписки", callback_data="list"),
            InlineKeyboardButton(text=" Добавить", callback_data="add")
        ],
        [
            InlineKeyboardButton(text=" Прогноз", callback_data="forecast"),
            InlineKeyboardButton(text=" Премиум", callback_data="premium")
        ]
    ])

def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории"""
    buttons = []
    for category in Category:
        buttons.append([InlineKeyboardButton(
            text=category.value.capitalize(),
            callback_data=f"cat_{category.value}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периодичности"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Ежемесячно", callback_data="period_monthly")],
        [InlineKeyboardButton(text=" Раз в 3 месяца", callback_data="period_quarterly")],
        [InlineKeyboardButton(text=" Раз в год", callback_data="period_yearly")],
        [InlineKeyboardButton(text="⚙ Своя периодичность", callback_data="period_custom")]
    ])

def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Ручной", callback_data="payment_manual")],
        [InlineKeyboardButton(text=" Через диалог с ботом", callback_data="payment_dialog")]
    ])

def get_subscription_actions(subscription_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с подпиской"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=" Отметить оплату", callback_data=f"pay_{subscription_id}"),
            InlineKeyboardButton(text=" Редактировать", callback_data=f"edit_{subscription_id}")
        ],
        [
            InlineKeyboardButton(text=" Приостановить", callback_data=f"pause_{subscription_id}"),
            InlineKeyboardButton(text=" Удалить", callback_data=f"delete_{subscription_id}")
        ],
        [InlineKeyboardButton(text=" Главное меню", callback_data="back_to_menu")]
    ])

def get_premium_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для премиум"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить премиум (99₽/мес)", callback_data="buy_premium")],
        [InlineKeyboardButton(text=" Главное меню", callback_data="back_to_menu")]
    ])

def get_confirm_payment_keyboard(subscription_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения платежа"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=" Да, списать", callback_data=f"confirm_pay_{subscription_id}"),
            InlineKeyboardButton(text=" Отложить", callback_data=f"delay_pay_{subscription_id}")
        ],
        [InlineKeyboardButton(text=" Главное меню", callback_data="back_to_menu")]
    ])

def get_back_button() -> InlineKeyboardMarkup:
    """Кнопка назад в главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Главное меню", callback_data="back_to_menu")]
    ])