import os
import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from config import DATABASE_URL
from models import Subscription, User, Payment, Category, Period, PaymentMethod, SubscriptionStatus, UserStatus


class Database:
    def __init__(self):
        self.conn = None
        self.pool = None
        # Определяем тип базы данных
        self.use_sqlite = not DATABASE_URL or DATABASE_URL.startswith('sqlite://')

    async def init(self):
        """Инициализация базы данных"""
        if self.use_sqlite:
            # Получаем директорию проекта (где находится main.py)
            current_dir = os.path.dirname(os.path.abspath(__file__))

            # Используем SQLite с путём в директории проекта
            if DATABASE_URL and DATABASE_URL.startswith('sqlite://'):
                db_path = DATABASE_URL.replace('sqlite://', '')
                # Если путь относительный, делаем его абсолютным
                if not os.path.isabs(db_path):
                    db_path = os.path.join(current_dir, db_path)
            else:
                db_path = os.path.join(current_dir, 'subscription_bot.db')

            # Убеждаемся, что директория существует
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            print(f"Подключение к SQLite базе данных: {db_path}")

            # Подключаемся с правильными параметрами
            try:
                self.conn = await aiosqlite.connect(
                    db_path,
                    timeout=30,  # Таймаут ожидания блокировки
                    isolation_level=None  # Автоматический commit
                )

                # Включаем поддержку внешних ключей
                await self.conn.execute("PRAGMA foreign_keys = ON")

                # Создаем таблицы
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        status TEXT DEFAULT 'active',
                        premium_until TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        amount REAL NOT NULL,
                        period TEXT NOT NULL,
                        period_days INTEGER NOT NULL,
                        next_payment_date DATE NOT NULL,
                        payment_method TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        subscription_id INTEGER NOT NULL,
                        amount REAL NOT NULL,
                        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confirmed INTEGER DEFAULT 1,
                        FOREIGN KEY (subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS premium_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        amount REAL NOT NULL,
                        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        valid_until TIMESTAMP NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')

                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS yookassa_payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        payment_id TEXT UNIQUE NOT NULL,
                        amount REAL NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confirmed_at TIMESTAMP,
                        valid_until TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')

                await self.conn.commit()
                print("SQLite база данных успешно инициализирована")

            except Exception as e:
                print(f"Ошибка при подключении к базе данных: {e}")
                raise

        else:
            # Используем PostgreSQL
            import asyncpg
            try:
                self.pool = await asyncpg.create_pool(DATABASE_URL)
                print("PostgreSQL база данных инициализирована")
            except Exception as e:
                print(f"Ошибка подключения к PostgreSQL: {e}")
                raise

    async def get_or_create_user(self, telegram_id: int, username: Optional[str]) -> User:
        """Получить или создать пользователя"""
        if self.use_sqlite:
            cursor = await self.conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()

            if not row:
                cursor = await self.conn.execute(
                    "INSERT INTO users (telegram_id, username) VALUES (?, ?) RETURNING id, telegram_id, username, status, premium_until, created_at",
                    (telegram_id, username)
                )
                row = await cursor.fetchone()
                await self.conn.commit()

            if row:
                return User(
                    id=row[0],
                    telegram_id=row[1],
                    username=row[2],
                    status=UserStatus(row[3]),
                    premium_until=datetime.fromisoformat(row[4]) if row[4] else None,
                    created_at=datetime.fromisoformat(row[5])
                )
        else:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE telegram_id = $1",
                    telegram_id
                )

                if not row:
                    row = await conn.fetchrow(
                        "INSERT INTO users (telegram_id, username) VALUES ($1, $2) RETURNING *",
                        telegram_id, username
                    )

                return User(
                    id=row['id'],
                    telegram_id=row['telegram_id'],
                    username=row['username'],
                    status=UserStatus(row['status']),
                    premium_until=row['premium_until'],
                    created_at=row['created_at']
                )
        return None

    async def get_user_subscriptions_count(self, user_id: int) -> int:
        """Получить количество активных подписок пользователя"""
        if self.use_sqlite:
            cursor = await self.conn.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE user_id = ? AND status = 'active'",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
        else:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT COUNT(*) FROM subscriptions WHERE user_id = $1 AND status = 'active'",
                    user_id
                )
                return row['count']

    async def can_add_subscription(self, user_id: int) -> tuple[bool, str]:
        """Проверить, может ли пользователь добавить новую подписку"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, "Пользователь не найден"

        count = await self.get_user_subscriptions_count(user_id)

        if user.status == UserStatus.PREMIUM:
            if user.premium_until and user.premium_until < datetime.now():
                # Премиум истек
                await self.update_user_status(user_id, UserStatus.ACTIVE)
                if count >= 3:
                    return False, "Ваш премиум истек. У вас уже есть 3 активные подписки. Для добавления новых необходимо продлить премиум (99₽/мес)"
                return True, "ok"
            return True, "ok"
        else:
            if count >= 3:
                return False, f"У вас уже есть 3 активные подписки (бесплатный лимит). Для добавления новых подписок необходимо оформить премиум за 99₽/мес"
            return True, "ok"

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по внутреннему ID"""
        if self.use_sqlite:
            cursor = await self.conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return User(
                    id=row[0],
                    telegram_id=row[1],
                    username=row[2],
                    status=UserStatus(row[3]),
                    premium_until=datetime.fromisoformat(row[4]) if row[4] else None,
                    created_at=datetime.fromisoformat(row[5])
                )
        else:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                if row:
                    return User(
                        id=row['id'],
                        telegram_id=row['telegram_id'],
                        username=row['username'],
                        status=UserStatus(row['status']),
                        premium_until=row['premium_until'],
                        created_at=row['created_at']
                    )
        return None

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        if self.use_sqlite:
            cursor = await self.conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            if row:
                return User(
                    id=row[0],
                    telegram_id=row[1],
                    username=row[2],
                    status=UserStatus(row[3]),
                    premium_until=datetime.fromisoformat(row[4]) if row[4] else None,
                    created_at=datetime.fromisoformat(row[5])
                )
        else:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE telegram_id = $1",
                    telegram_id
                )
                if row:
                    return User(
                        id=row['id'],
                        telegram_id=row['telegram_id'],
                        username=row['username'],
                        status=UserStatus(row['status']),
                        premium_until=row['premium_until'],
                        created_at=row['created_at']
                    )
        return None

    async def update_user_status(self, user_id: int, status: UserStatus):
        """Обновить статус пользователя"""
        if self.use_sqlite:
            await self.conn.execute(
                "UPDATE users SET status = ? WHERE id = ?",
                (status.value, user_id)
            )
            await self.conn.commit()
        else:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET status = $1 WHERE id = $2",
                    status.value, user_id
                )

    async def add_subscription(self, user_id: int, name: str, category: Category,
                               amount: float, period: Period, period_days: int,
                               next_payment_date: datetime, payment_method: PaymentMethod) -> int:
        """Добавить подписку"""
        if self.use_sqlite:
            cursor = await self.conn.execute(
                """INSERT INTO subscriptions 
                   (user_id, name, category, amount, period, period_days, next_payment_date, payment_method)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                (user_id, name, category.value, amount, period.value, period_days,
                 next_payment_date.date(), payment_method.value)
            )
            row = await cursor.fetchone()
            await self.conn.commit()
            return row[0] if row else 0
        else:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """INSERT INTO subscriptions 
                       (user_id, name, category, amount, period, period_days, next_payment_date, payment_method)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id""",
                    user_id, name, category.value, amount, period.value, period_days,
                    next_payment_date, payment_method.value
                )
                return row['id']

    async def get_user_subscriptions(self, user_id: int, include_inactive: bool = False) -> List[Dict]:
        """Получить подписки пользователя"""
        if self.use_sqlite:
            query = "SELECT * FROM subscriptions WHERE user_id = ?"
            params = [user_id]
            if not include_inactive:
                query += " AND status = 'active'"
            query += " ORDER BY next_payment_date"

            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()

            # Преобразуем row в dict
            subscriptions = []
            for row in rows:
                subscriptions.append({
                    'id': row[0],
                    'user_id': row[1],
                    'name': row[2],
                    'category': row[3],
                    'amount': row[4],
                    'period': row[5],
                    'period_days': row[6],
                    'next_payment_date': datetime.strptime(row[7], '%Y-%m-%d').date(),
                    'payment_method': row[8],
                    'status': row[9],
                    'created_at': row[10]
                })
            return subscriptions
        else:
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM subscriptions WHERE user_id = $1"
                if not include_inactive:
                    query += " AND status = 'active'"
                query += " ORDER BY next_payment_date"

                rows = await conn.fetch(query, user_id)
                return [dict(row) for row in rows]

    async def get_subscription(self, subscription_id: int) -> Optional[Dict]:
        """Получить подписку по ID"""
        if self.use_sqlite:
            cursor = await self.conn.execute(
                "SELECT * FROM subscriptions WHERE id = ?",
                (subscription_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'name': row[2],
                    'category': row[3],
                    'amount': row[4],
                    'period': row[5],
                    'period_days': row[6],
                    'next_payment_date': datetime.strptime(row[7], '%Y-%m-%d').date(),
                    'payment_method': row[8],
                    'status': row[9],
                    'created_at': row[10]
                }
        else:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM subscriptions WHERE id = $1",
                    subscription_id
                )
                return dict(row) if row else None
        return None

    async def update_subscription(self, subscription_id: int, **kwargs):
        """Обновить подписку"""
        if self.use_sqlite:
            for key, value in kwargs.items():
                await self.conn.execute(
                    f"UPDATE subscriptions SET {key} = ? WHERE id = ?",
                    (value, subscription_id)
                )
            await self.conn.commit()
        else:
            async with self.pool.acquire() as conn:
                fields = []
                values = []
                for i, (key, value) in enumerate(kwargs.items(), 1):
                    fields.append(f"{key} = ${i}")
                    values.append(value)

                if fields:
                    query = f"UPDATE subscriptions SET {', '.join(fields)} WHERE id = ${len(values) + 1}"
                    values.append(subscription_id)
                    await conn.execute(query, *values)

    async def delete_subscription(self, subscription_id: int):
        """Удалить подписку"""
        if self.use_sqlite:
            await self.conn.execute(
                "UPDATE subscriptions SET status = 'deleted' WHERE id = ?",
                (subscription_id,)
            )
            await self.conn.commit()
        else:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE subscriptions SET status = 'deleted' WHERE id = $1",
                    subscription_id
                )

    async def record_payment(self, subscription_id: int, amount: float) -> int:
        """Записать платеж и обновить дату следующего платежа"""
        if self.use_sqlite:
            # Записываем платеж
            cursor = await self.conn.execute(
                "INSERT INTO payments (subscription_id, amount) VALUES (?, ?) RETURNING id",
                (subscription_id, amount)
            )
            payment_row = await cursor.fetchone()
            payment_id = payment_row[0] if payment_row else 0

            # Получаем подписку
            cursor = await self.conn.execute(
                "SELECT * FROM subscriptions WHERE id = ?",
                (subscription_id,)
            )
            sub = await cursor.fetchone()

            if sub:
                # Обновляем дату следующего платежа
                new_date = datetime.now() + timedelta(days=sub[6])
                await self.conn.execute(
                    "UPDATE subscriptions SET next_payment_date = ? WHERE id = ?",
                    (new_date.date(), subscription_id)
                )
                await self.conn.commit()
            return payment_id
        else:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Записываем платеж
                    row = await conn.fetchrow(
                        "INSERT INTO payments (subscription_id, amount) VALUES ($1, $2) RETURNING id",
                        subscription_id, amount
                    )

                    # Получаем подписку
                    sub = await conn.fetchrow(
                        "SELECT * FROM subscriptions WHERE id = $1",
                        subscription_id
                    )

                    # Обновляем дату следующего платежа
                    new_date = datetime.now() + timedelta(days=sub['period_days'])
                    await conn.execute(
                        "UPDATE subscriptions SET next_payment_date = $1 WHERE id = $2",
                        new_date, subscription_id
                    )

                    return row['id']

    async def get_upcoming_payments(self, user_id: int, days: int = 30) -> List[Dict]:
        """Получить предстоящие платежи"""
        if self.use_sqlite:
            cursor = await self.conn.execute(
                """SELECT * FROM subscriptions 
                   WHERE user_id = ? AND status = 'active' 
                   AND date(next_payment_date) BETWEEN date('now') AND date('now', '+' || ? || ' days')
                   ORDER BY next_payment_date""",
                (user_id, days)
            )
            rows = await cursor.fetchall()
            subscriptions = []
            for row in rows:
                subscriptions.append({
                    'id': row[0],
                    'name': row[2],
                    'amount': row[4],
                    'next_payment_date': datetime.strptime(row[7], '%Y-%m-%d').date(),
                    'payment_method': row[8]
                })
            return subscriptions
        else:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT * FROM subscriptions 
                       WHERE user_id = $1 AND status = 'active' 
                       AND next_payment_date BETWEEN CURRENT_DATE AND CURRENT_DATE + $2 * INTERVAL '1 day'
                       ORDER BY next_payment_date""",
                    user_id, days
                )
                return [dict(row) for row in rows]

    async def add_premium_transaction(self, user_id: int, amount: float, valid_until: datetime):
        """Добавить премиум транзакцию"""
        if self.use_sqlite:
            await self.conn.execute(
                "INSERT INTO premium_transactions (user_id, amount, valid_until) VALUES (?, ?, ?)",
                (user_id, amount, valid_until)
            )
            await self.conn.execute(
                "UPDATE users SET status = 'premium', premium_until = ? WHERE id = ?",
                (valid_until, user_id)
            )
            await self.conn.commit()
        else:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO premium_transactions (user_id, amount, valid_until) VALUES ($1, $2, $3)",
                    user_id, amount, valid_until
                )
                await conn.execute(
                    "UPDATE users SET status = 'premium', premium_until = $1 WHERE id = $2",
                    valid_until, user_id
                )

    async def get_forecast(self, user_id: int) -> Dict[str, Any]:
        """Получить прогноз расходов"""
        subscriptions = await self.get_user_subscriptions(user_id)
        total = sum(s['amount'] for s in subscriptions)

        by_category = {}
        for sub in subscriptions:
            cat = sub['category']
            by_category[cat] = by_category.get(cat, 0) + sub['amount']

        upcoming = await self.get_upcoming_payments(user_id, 30)

        return {
            'total_monthly': total,
            'by_category': by_category,
            'upcoming': upcoming,
            'subscriptions_count': len(subscriptions)
        }

    async def close(self):
        """Закрыть соединение с БД"""
        if self.use_sqlite:
            if self.conn:
                await self.conn.close()
                print("Соединение с SQLite закрыто")
        else:
            if self.pool:
                await self.pool.close()
                print("Соединение с PostgreSQL закрыто")


db = Database()