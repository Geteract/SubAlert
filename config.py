import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Стоимость премиум подписки в месяц
PREMIUM_PRICE = 99

# Бесплатный лимит подписок
FREE_SUBSCRIPTION_LIMIT = 3