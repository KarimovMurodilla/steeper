# Steeper

Telegram bot middleware that syncs incoming user messages and outgoing bot replies with the **Steeper** platform.

## Installation

```bash
# Core (pick one extra for your framework)
pip install steeper[aiogram]     # aiogram v3
pip install steeper[telebot]     # pyTelegramBotAPI
pip install steeper[ptb]         # python-telegram-bot v20+
```

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
from aiogram import Bot, Dispatcher
from steeper.integrations.aiogram import SteeperMiddleware

BOT_TOKEN = "123456:ABC-DEF..."
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

steeper = SteeperMiddleware(
    base_url="http://localhost:8000",
    bot_id="your-bot-uuid",
    bot_token=BOT_TOKEN,
)
steeper.setup(dp, bot)

# ... register your handlers as usual ...
dp.run_polling(bot)
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

1. **Incoming messages** — the middleware intercepts every Telegram Update, serializes it to the standard Telegram JSON format, and POSTs it to the Steeper webhook endpoint. Your handlers still run normally.

2. **Outgoing messages** — `Bot.send_message` is patched so that every bot reply is also logged to the Steeper bot-message endpoint.

Both operations are fire-and-forget: if the Steeper backend is unreachable, a warning is logged but your bot continues to work.

## License

MIT
