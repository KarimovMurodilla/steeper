"""Minimal aiogram v3 bot wired to Steeper, with system-log capture and funnel events.

Run:
    pip install steeper[aiogram]
    export BOT_TOKEN=...        # from BotFather
    export STEEPER_BOT_ID=...   # UUID of the bot registered in Steeper
    export STEEPER_BASE_URL=http://localhost:8000
    python examples/aiogram_bot.py
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from steeper import EventTracker
from steeper.integrations.aiogram import SteeperMiddleware

BOT_TOKEN = os.environ["BOT_TOKEN"]
STEEPER_BOT_ID = os.environ["STEEPER_BOT_ID"]
STEEPER_BASE_URL = os.environ.get("STEEPER_BASE_URL", "http://localhost:8000")

# Steeper captures whatever the stdlib logging setup produces, so configure
# logging the way you normally would; the handler is added on top of it.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

logger = logging.getLogger("example.aiogram")

router = Router()


# Handlers depend on the tracker, not on the middleware. aiogram injects it by
# parameter name from the dispatcher's workflow data — see main(). The tracker
# knows nothing about Telegram or aiogram, so a handler taking it can be tested
# with a fake and no HTTP client, dispatcher or setup() in sight.
@router.message(CommandStart())
async def cmd_start(message: Message, tracker: EventTracker) -> None:
    # `extra` fields travel with the record and are shown in the panel.
    logger.info("start command", extra={"chat_id": message.chat.id})
    # Telegram traffic alone cannot say the user signed up — the bot has to.
    # This is the event a funnel's first step matches on.
    tracker.track("signup", user_id=message.from_user.id)
    await message.answer("Hello from a Steeper-synced bot! Try /buy.")


@router.message(Command("buy"))
async def cmd_buy(message: Message, tracker: EventTracker) -> None:
    tracker.track("checkout_started", user_id=message.from_user.id, props={"plan": "pro"})
    await message.answer("Pretend you paid. Check the Funnels page in Steeper.")
    tracker.track("payment_succeeded", user_id=message.from_user.id, props={"amount": 4900})


@router.message(Command("boom"))
async def cmd_boom(message: Message) -> None:
    """Deliberately fail, to see a traceback show up in the Steeper panel."""
    try:
        raise RuntimeError("something went wrong in a handler")
    except RuntimeError:
        logger.exception("handler failed", extra={"chat_id": message.chat.id})
    await message.answer("Logged an error — check the Logs page in Steeper.")


async def main() -> None:
    steeper = SteeperMiddleware(
        base_url=STEEPER_BASE_URL,
        bot_id=STEEPER_BOT_ID,
        bot_token=BOT_TOKEN,
        # Also mirror this process's logging output to the platform. Off by
        # default; `log_level="DEBUG"` on a chatty bot is a lot of traffic.
        capture_logs=True,
        log_level="INFO",
    )

    bot = Bot(token=BOT_TOKEN)
    # Anything passed here lands in the dispatcher's workflow data, which
    # aiogram injects into handlers by parameter name. A DI container would go
    # in the same place; the tracker is an ordinary dependency either way.
    dp = Dispatcher(tracker=steeper.tracker)
    dp.include_router(router)

    # Past this line the middleware is not referred to again: it is registered
    # with the framework, which is all a middleware should be.
    steeper.setup(dp, bot)

    logger.info("bot starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
