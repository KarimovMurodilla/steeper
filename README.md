# Steeper

[![PyPI version](https://img.shields.io/pypi/v/steeper.svg)](https://pypi.org/project/steeper/)
[![Python versions](https://img.shields.io/pypi/pyversions/steeper.svg)](https://pypi.org/project/steeper/)
[![CI](https://github.com/KarimovMurodilla/steeper/actions/workflows/ci.yml/badge.svg)](https://github.com/KarimovMurodilla/steeper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Telegram bot middleware that syncs incoming user messages and outgoing bot replies with the **Steeper** platform.

## Installation

```bash
# Core (pick one extra for your framework)
pip install steeper[aiogram]     # aiogram v3
pip install steeper[telebot]     # pyTelegramBotAPI
pip install steeper[ptb]         # python-telegram-bot v20+
```

> **Need a backend?** Steeper is self-hosted. Run the Steeper backend (Docker Compose), create a superuser, and register a bot to get its `bot_id`. Point `base_url` at your instance. <!-- TODO: link to the backend repo / self-hosting guide -->

Runnable examples for every framework live in [`examples/`](examples/). For the
big picture — platform, library, and how they interact — see
[`docs/OVERVIEW.md`](docs/OVERVIEW.md).

## Configuration

Every integration requires three values:

| Parameter   | Description                                  |
|-------------|----------------------------------------------|
| `base_url`  | Steeper backend URL (e.g. `http://localhost:8000`) |
| `bot_id`    | UUID of the bot registered in Steeper        |
| `bot_token` | Raw Telegram bot token from BotFather        |

## Usage

### aiogram v3

```python
import asyncio

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from steeper.integrations.aiogram import SteeperMiddleware

BOT_TOKEN = "123456:ABC-DEF..."

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer("Hello!")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    steeper = SteeperMiddleware(
        base_url="http://localhost:8000",
        bot_id="your-bot-uuid",
        bot_token=BOT_TOKEN,
    )
    steeper.setup(dp, bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

### pyTelegramBotAPI (telebot)

```python
import telebot
from steeper.integrations.telebot import SteeperMiddleware

BOT_TOKEN = "123456:ABC-DEF..."
bot = telebot.TeleBot(BOT_TOKEN)

steeper = SteeperMiddleware(
    base_url="http://localhost:8000",
    bot_id="your-bot-uuid",
    bot_token=BOT_TOKEN,
)
steeper.setup(bot)

# ... register your handlers as usual ...
bot.polling()
```

### python-telegram-bot v20+

```python
from telegram.ext import ApplicationBuilder
from steeper.integrations.ptb import SteeperMiddleware

BOT_TOKEN = "123456:ABC-DEF..."
app = ApplicationBuilder().token(BOT_TOKEN).build()

steeper = SteeperMiddleware(
    base_url="http://localhost:8000",
    bot_id="your-bot-uuid",
    bot_token=BOT_TOKEN,
)
steeper.setup(app)

# ... register your handlers as usual ...
app.run_polling()
```

## How it works

All HTTP calls to Steeper go through **`SteeperRepository`** (`steeper.repository`): it forwards **incoming** updates and records **outgoing** bot messages to your backend. Each `SteeperMiddleware` exposes `.repository` (and `.client` for the underlying async HTTP client).

1. **Incoming** — the integration passes the **full** Telegram update, as Telegram-shaped JSON, to `repository.forward_update(...)` (every update type — messages, callback queries, inline queries, etc. — with all fields preserved). Your handlers still run as usual.

2. **Outgoing** — the integration hooks the framework so bot-originated messages are turned into `OutgoingMessageSnapshot` values and sent with `repository.record_outgoing(...)`.
   - **aiogram** — `Bot.__call__` is wrapped so any API call whose result is a `Message` (or a list of them, e.g. media groups) is logged—not only `send_message`.
   - **python-telegram-bot** — `Bot._post` is wrapped so JSON responses that decode to `Message` instances are logged (sends, edits, media groups, etc.).
   - **telebot** — `telebot.apihelper._make_request` is wrapped for your bot token so JSON `result` payloads that contain full `message` objects are logged.

If you bypass the normal API (e.g. raw HTTP to Telegram), call the repository yourself:

```python
from steeper.repository import OutgoingMessageSnapshot

await steeper.repository.record_outgoing(
    OutgoingMessageSnapshot(
        chat_id=chat_id,
        message_id=message_id,
        text="visible text or caption",
        date=None,  # optional Unix ts; if omitted, the client defaults it to the current time
    )
)
```

Failures are never fatal: if the Steeper backend is unreachable or returns an error, a warning is logged and your bot keeps working. Note the dispatch model differs per framework — for **aiogram** and **python-telegram-bot** the sync calls are awaited inline, so a slow or unreachable backend can add latency (up to the client timeout, 10s by default) per update; **telebot** dispatches them as background tasks.

## Backend compatibility

This library talks to the Steeper backend's **`/v1`** HTTP API:

Both endpoints identify the bot by `bot_id` in the path and authenticate with the secret (`token_hash` = SHA-256 of the bot token) in the `x-telegram-bot-api-secret-token` header — the secret never appears in the URL.

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/communications/webhook/{bot_id}` | Forward incoming Telegram updates |
| `POST /v1/communications/webhook/{bot_id}/bot-message` | Record outgoing bot messages |

| `steeper` (library) | Steeper backend |
|---------------------|-----------------|
| `0.2.x`             | bot-message authenticated via header (current) |
| `0.1.x`             | bot-message authenticated via `token_hash` in the URL path (legacy) |

`0.2.0` changed the outgoing endpoint's contract, so a `0.2.x` client needs a backend built with the matching change (and vice-versa). See [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).
