"""Minimal aiogram v3 bot wired to Steeper, with system-log capture.

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

from steeper.integrations.aiogram import SteeperMiddleware

BOT_TOKEN = os.environ["BOT_TOKEN"]
STEEPER_BOT_ID = os.environ["STEEPER_BOT_ID"]
STEEPER_BASE_URL = os.environ.get("STEEPER_BASE_URL", "http://localhost:8000")

# Steeper captures whatever the stdlib logging setup produces, so configure
# logging the way you normally would; the handler is added on top of it.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

logger = logging.getLogger("example.aiogram")

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    # `extra` fields travel with the record and are shown in the panel.
    logger.info("start command", extra={"chat_id": message.chat.id})
    await message.answer("Hello from a Steeper-synced bot!")


@router.message(Command("boom"))
async def cmd_boom(message: Message) -> None:
    """Deliberately fail, to see a traceback show up in the Steeper panel."""
    try:
        raise RuntimeError("something went wrong in a handler")
    except RuntimeError:
        logger.exception("handler failed", extra={"chat_id": message.chat.id})
    await message.answer("Logged an error — check the Logs page in Steeper.")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    SteeperMiddleware(
        base_url=STEEPER_BASE_URL,
        bot_id=STEEPER_BOT_ID,
        bot_token=BOT_TOKEN,
        # Also mirror this process's logging output to the platform. Off by
        # default; `log_level="DEBUG"` on a chatty bot is a lot of traffic.
        capture_logs=True,
        log_level="INFO",
    ).setup(dp, bot)

    logger.info("bot starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
