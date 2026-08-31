"""Minimal pyTelegramBotAPI (telebot) bot wired to Steeper, with system-log capture.

Run:
    pip install steeper[telebot]
    export BOT_TOKEN=...        # from BotFather
    export STEEPER_BOT_ID=...   # UUID of the bot registered in Steeper
    export STEEPER_BASE_URL=http://localhost:8000
    python examples/telebot_bot.py
"""

import logging
import os

import telebot

from steeper.integrations.telebot import SteeperMiddleware

BOT_TOKEN = os.environ["BOT_TOKEN"]
STEEPER_BOT_ID = os.environ["STEEPER_BOT_ID"]
STEEPER_BASE_URL = os.environ.get("STEEPER_BASE_URL", "http://localhost:8000")

# Steeper captures whatever the stdlib logging setup produces, so configure
# logging the way you normally would; the handler is added on top of it.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

logger = logging.getLogger("example.telebot")

bot = telebot.TeleBot(BOT_TOKEN)

steeper = SteeperMiddleware(
    base_url=STEEPER_BASE_URL,
    bot_id=STEEPER_BOT_ID,
    bot_token=BOT_TOKEN,
    # Also mirror this process's logging output to the platform. Off by
    # default; `log_level="DEBUG"` on a chatty bot is a lot of traffic.
    capture_logs=True,
    log_level="INFO",
)
steeper.setup(bot)


@bot.message_handler(commands=["start"])
def cmd_start(message: telebot.types.Message) -> None:
    # `extra` fields travel with the record and are shown in the panel.
    logger.info("start command", extra={"chat_id": message.chat.id})
    bot.reply_to(message, "Hello from a Steeper-synced bot!")


@bot.message_handler(commands=["boom"])
def cmd_boom(message: telebot.types.Message) -> None:
    """Deliberately fail, to see a traceback show up in the Steeper panel."""
    try:
        raise RuntimeError("something went wrong in a handler")
    except RuntimeError:
        logger.exception("handler failed", extra={"chat_id": message.chat.id})
    bot.reply_to(message, "Logged an error — check the Logs page in Steeper.")


if __name__ == "__main__":
    logger.info("bot starting")
    try:
        bot.polling()
    finally:
        # telebot is synchronous and has no shutdown hook, so close Steeper by
        # hand: this also flushes any log records still buffered. aiogram and
        # python-telegram-bot do it for you.
        steeper.close()
