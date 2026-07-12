import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# ─── Telegram ───
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# ─── AI Providers ───
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ─── Server ───
PORT = int(os.getenv("PORT", "8000"))
