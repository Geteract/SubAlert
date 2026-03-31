from enum import Enum
from datetime import datetime
from typing import Optional

class Category(str, Enum):
    RENT = "аренда"
    INSTALLMENT = "рассрочка"
    INSURANCE = "страховка"
    SERVICE = "сервис"
    OTHER = "другое"

class Period(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class PaymentMethod(str, Enum):
    MANUAL = "manual"
    DIALOG = "dialog"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"

class UserStatus(str, Enum):
    ACTIVE = "active"
    PREMIUM = "premium"
    BLOCKED = "blocked"

class Subscription:
    def __init__(self, id: int, user_id: int, name: str, category: Category,
                 amount: float, period: Period, period_days: int,
                 next_payment_date: datetime, payment_method: PaymentMethod,
                 status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
                 created_at: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.category = category
        self.amount = amount
        self.period = period
        self.period_days = period_days
        self.next_payment_date = next_payment_date
        self.payment_method = payment_method
        self.status = status
        self.created_at = created_at or datetime.now()

class User:
    def __init__(self, id: int, telegram_id: int, username: Optional[str],
                 status: UserStatus, premium_until: Optional[datetime],
                 created_at: datetime):
        self.id = id
        self.telegram_id = telegram_id
        self.username = username
        self.status = status
        self.premium_until = premium_until
        self.created_at = created_at

class Payment:
    def __init__(self, id: int, subscription_id: int, amount: float,
                 payment_date: datetime, confirmed: bool = True):
        self.id = id
        self.subscription_id = subscription_id
        self.amount = amount
        self.payment_date = payment_date
        self.confirmed = confirmed