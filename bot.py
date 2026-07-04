import logging
import os
import threading
from flask import Flask

flask_app = Flask(__name__)

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from config import (
    TELEGRAM_BOT_TOKEN,
    KIMI_API_KEY,
    KIMI_API_URL,
    KIMI_MODEL,
    PORT,
    WEBHOOK_URL,
)
from utils import detect_language, get_texts

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

user_lang: dict[int, str] = {}


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not isinstance(msg, Message):
        return
    uid = update.effective_user.id
    code = (update.effective_user.language_code or "en").lower()
    user_lang[uid] = "ru" if code.startswith("ru") else "en"
    t = get_texts(user_lang[uid])
    await msg.reply_text(t["welcome"])


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not isinstance(msg, Message):
        return
    uid = update.effective_user.id
    lang = user_lang.get(uid, "en")
    t = get_texts(lang)
    await msg.reply_text(t["help"])


async def fetch_recipes(ingredients: str, lang: str) -> str:
    t = get_texts(lang)
    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": KIMI_MODEL,
        "messages": [
            {"role": "system", "content": t["system_prompt"]},
            {"role": "user", "content": t["user_prompt"].format(ingredients=ingredients)},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(KIMI_API_URL, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Kimi API {resp.status_code}: {resp.text}")


async def handle_ingredients(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not isinstance(msg, Message) or not msg.text:
        return
    ingredients = msg.text
    user = update.effective_user
    uid = user.id
    lang = detect_language(ingredients)
    user_lang[uid] = lang
    t = get_texts(lang)
    logger.info("User %s (%s) sent: %s", uid, user.username, ingredients)
    processing_msg = await msg.reply_text(t["processing"])
    try:
        recipes = await fetch_recipes(ingredients, lang)
        await processing_msg.delete()
        keyboard = [[InlineKeyboardButton(t["restart_btn"], callback_data="restart")]]
        markup = InlineKeyboardMarkup(keyboard)
        if len(recipes) > 4096:
            parts = [recipes[i : i + 4000] for i in range(0, len(recipes), 4000)]
            for i, part in enumerate(parts):
                prefix = f"📄 Part {i + 1}/{len(parts)}\n\n" if len(parts) > 1 else ""
                if i == len(parts) - 1:
                    await msg.reply_text(prefix + part, reply_markup=markup)
                else:
                    await msg.reply_text(prefix + part)
        else:
            await msg.reply_text(
                f"{t['recipes_header']}\n\n{recipes}",
                reply_markup=markup,
            )
    except Exception as exc:
        logger.error("Error: %s", exc)
        await processing_msg.edit_text(t["error"])


async def restart_callback(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    uid = update.effective_user.id
    lang = user_lang.get(uid, "en")
    t = get_texts(lang)
    await query.edit_message_reply_markup(reply_markup=None)
    callback_msg = query.message
    if isinstance(callback_msg, Message):
        await callback_msg.reply_text(t["restart_prompt"])


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Update %s caused error %s", update, context.error)
    err_msg = update.message
    if isinstance(err_msg, Message):
        await err_msg.reply_text("😔 Unexpected error. Please try again.")


def run_bot() -> None:
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("ВАШ_"):
        raise SystemExit("❌ Укажите TELEGRAM_BOT_TOKEN в .env!")
    if not KIMI_API_KEY or KIMI_API_KEY.startswith("ВАШ_"):
        raise SystemExit("❌ Укажите KIMI_API_KEY в .env!")

    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CallbackQueryHandler(restart_callback, pattern="^restart$"))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ingredients))
    telegram_app.add_error_handler(error_handler)
    logger.info("🤖 Bot started!")

    if WEBHOOK_URL:
        telegram_app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
            stop_signals=None,
        )
    else:
        telegram_app.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)


@flask_app.route('/')
def health():
    return "Bot is running", 200


if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host='0.0.0.0', port=port)