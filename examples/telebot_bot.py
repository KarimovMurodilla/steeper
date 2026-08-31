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

from steeper import EventTracker
from steeper.integrations.telebot import SteeperMiddleware

BOT_TOKEN = os.environ["BOT_TOKEN"]
STEEPER_BOT_ID = os.environ["STEEPER_BOT_ID"]
STEEPER_BASE_URL = os.environ.get("STEEPER_BASE_URL", "http://localhost:8000")

# Steeper captures whatever the stdlib logging setup produces, so configure
# logging the way you normally would; the handler is added on top of it.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

logger = logging.getLogger("example.telebot")

bot = telebot.TeleBot(BOT_TOKEN)

_steeper = SteeperMiddleware(
    base_url=STEEPER_BASE_URL,
    bot_id=STEEPER_BOT_ID,
    bot_token=BOT_TOKEN,
    # Also mirror this process's logging output to the platform. Off by
    # default; `log_level="DEBUG"` on a chatty bot is a lot of traffic.
    capture_logs=True,
    log_level="INFO",
)
_steeper.setup(bot)

# pyTelegramBotAPI is synchronous and has neither DI nor a context object: a
# handler's signature is fixed at `(message)`, so there is nothing to inject
# through. A module-level name is the only option here — but it is the tracker,
# not the middleware, so handlers still depend on `track` alone and stay
# testable by passing a fake in. The aiogram and PTB examples inject it instead.
tracker: EventTracker = _steeper.tracker


@bot.message_handler(commands=["start"])
def cmd_start(message: telebot.types.Message) -> None:
    # `extra` fields travel with the record and are shown in the panel.
    logger.info("start command", extra={"chat_id": message.chat.id})
    # Telegram traffic alone cannot say the user signed up — the bot has to.
    # This is the event a funnel's first step matches on.
    tracker.track("signup", user_id=message.from_user.id)
    bot.reply_to(message, "Hello from a Steeper-synced bot! Try /buy.")


@bot.message_handler(commands=["buy"])
def cmd_buy(message: telebot.types.Message) -> None:
    tracker.track("checkout_started", user_id=message.from_user.id, props={"plan": "pro"})
    bot.reply_to(message, "Pretend you paid. Check the Funnels page in Steeper.")
    tracker.track("payment_succeeded", user_id=message.from_user.id, props={"amount": 4900})


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
        _steeper.close()
