"""Minimal python-telegram-bot v20+ bot wired to Steeper, with system-log capture.

Run:
    pip install steeper[ptb]
    export BOT_TOKEN=...        # from BotFather
    export STEEPER_BOT_ID=...   # UUID of the bot registered in Steeper
    export STEEPER_BASE_URL=http://localhost:8000
    python examples/ptb_bot.py
"""

import logging
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from steeper.integrations.ptb import SteeperMiddleware

BOT_TOKEN = os.environ["BOT_TOKEN"]
STEEPER_BOT_ID = os.environ["STEEPER_BOT_ID"]
STEEPER_BASE_URL = os.environ.get("STEEPER_BASE_URL", "http://localhost:8000")

# Steeper captures whatever the stdlib logging setup produces, so configure
# logging the way you normally would; the handler is added on top of it.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

logger = logging.getLogger("example.ptb")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        # `extra` fields travel with the record and are shown in the panel.
        logger.info("start command", extra={"chat_id": update.message.chat_id})
        await update.message.reply_text("Hello from a Steeper-synced bot!")


async def cmd_boom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deliberately fail, to see a traceback show up in the Steeper panel."""
    if not update.message:
        return
    try:
        raise RuntimeError("something went wrong in a handler")
    except RuntimeError:
        logger.exception("handler failed", extra={"chat_id": update.message.chat_id})
    await update.message.reply_text("Logged an error — check the Logs page in Steeper.")


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    SteeperMiddleware(
        base_url=STEEPER_BASE_URL,
        bot_id=STEEPER_BOT_ID,
        bot_token=BOT_TOKEN,
        # Also mirror this process's logging output to the platform. Off by
        # default; `log_level="DEBUG"` on a chatty bot is a lot of traffic.
        capture_logs=True,
        log_level="INFO",
    ).setup(app)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("boom", cmd_boom))

    logger.info("bot starting")
    app.run_polling()


if __name__ == "__main__":
    main()
