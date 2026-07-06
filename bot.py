import asyncio
import logging
import os
import threading

import httpx
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import (
    TELEGRAM_BOT_TOKEN,
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    WEBHOOK_URL,
)

from utils import detect_language, get_texts

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

user_lang: dict[int, str] = {}

flask_app = Flask(__name__)
telegram_app: Application | None = None
bot_loop: asyncio.AbstractEventLoop | None = None


# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    msg = update.message
    if not isinstance(msg, Message):
        return
    uid = update.effective_user.id
    code = (update.effective_user.language_code or "en").lower()
    user_lang[uid] = "ru" if code.startswith("ru") else "en"
    t = get_texts(user_lang[uid])
    await msg.reply_text(t["welcome"])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
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
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": t["system_prompt"]},
            {"role": "user", "content": t["user_prompt"].format(ingredients=ingredients)},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            raise Exception(f"DeepSeek API {resp.status_code}: {resp.text}")


async def handle_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
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
                prefix = f" Part {i + 1}/{len(parts)}\n\n" if len(parts) > 1 else ""
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


async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
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


# ========== SETUP ==========

def setup_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(restart_callback, pattern="^restart$"))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ingredients)
    )
    application.add_error_handler(error_handler)


# ========== BOT THREADS ==========
@flask_app.before_request
def log_request():
    logger.info("Request: %s %s", request.method, request.path)


def run_polling() -> None:
    global telegram_app
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    setup_handlers(telegram_app)

    async def polling_loop() -> None:
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        logger.info("🤖 Bot started in POLLING mode!")
        await asyncio.Event().wait()

    loop.run_until_complete(polling_loop())


def run_webhook_mode() -> None:
    global telegram_app, bot_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_loop = loop

    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    setup_handlers(telegram_app)

    async def webhook_loop() -> None:
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        logger.info("🤖 Bot started in WEBHOOK mode! URL: %s", WEBHOOK_URL)
        await asyncio.Event().wait()

    loop.run_until_complete(webhook_loop())


# ========== FLASK ROUTES ==========

@flask_app.route("/")
def health() -> tuple[str, int]:
    return "Bot is running", 200


@flask_app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook() -> tuple[str, int]:
    logger.info("=== WEBHOOK HIT ===")
    if telegram_app is None or bot_loop is None:
        logger.error("Bot not ready")
        return "Bot not ready", 503

    json_data = request.get_json(force=True, silent=True) or {}
    logger.info("Data keys: %s", list(json_data.keys()) if json_data else "empty")
    update = Update.de_json(json_data, telegram_app.bot)

    asyncio.run_coroutine_threadsafe(
        telegram_app.process_update(update),
        bot_loop,
    )
    return "OK", 200


# ========== MAIN ==========

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("ВАШ_"):
        raise SystemExit("❌ Укажите TELEGRAM_BOT_TOKEN в Environment Variables!")
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY.startswith("ВАШ_"):
        raise SystemExit("❌ Укажите DEEPSEEK_API_KEY в Environment Variables!")

    if WEBHOOK_URL:
        bot_thread = threading.Thread(target=run_webhook_mode, daemon=True)
    else:
        bot_thread = threading.Thread(target=run_polling, daemon=True)

    bot_thread.start()

    port = int(os.environ.get("PORT", "5000"))
    logger.info("Starting Flask on port %s", port)
    flask_app.run(host="0.0.0.0", port=port)

