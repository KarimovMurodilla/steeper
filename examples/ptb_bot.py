"""Minimal python-telegram-bot v20+ bot wired to Steeper.

Run:
    pip install steeper[ptb]
    export BOT_TOKEN=...        # from BotFather
    export STEEPER_BOT_ID=...   # UUID of the bot registered in Steeper
    export STEEPER_BASE_URL=http://localhost:8000
    python examples/ptb_bot.py
"""

import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from steeper.integrations.ptb import SteeperMiddleware

BOT_TOKEN = os.environ["BOT_TOKEN"]
STEEPER_BOT_ID = os.environ["STEEPER_BOT_ID"]
STEEPER_BASE_URL = os.environ.get("STEEPER_BASE_URL", "http://localhost:8000")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Hello from a Steeper-synced bot!")


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    SteeperMiddleware(
        base_url=STEEPER_BASE_URL,
        bot_id=STEEPER_BOT_ID,
        bot_token=BOT_TOKEN,
    ).setup(app)

    app.add_handler(CommandHandler("start", cmd_start))
    app.run_polling()


if __name__ == "__main__":
    main()
