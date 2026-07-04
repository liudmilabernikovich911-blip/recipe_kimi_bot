import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "6741495356:AAFn3FDBhqVHA1xo3z083qOjL00QVWi9Owg")
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "sk-XVmQ7b44Q5HYz0K1bvxBL3CCE6xha6bA1W0JOJUri1bFlBp4")
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")

PORT = int(os.getenv("PORT", "8080"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")