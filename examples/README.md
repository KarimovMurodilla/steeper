# Steeper examples

Runnable, minimal bots for each supported framework. Each reads its config from
environment variables so you can copy a file and run it as-is.

## Setup

1. Run a Steeper backend (self-hosted) and register a bot to get its `bot_id` (UUID).
2. Copy env and fill values:
   ```bash
   cp examples/.env.example examples/.env
   # edit examples/.env, then:
   set -a && . examples/.env && set +a
   ```
3. Install the example's framework and run it:
   ```bash
   pip install "steeper[aiogram]" && python examples/aiogram_bot.py
   pip install "steeper[telebot]" && python examples/telebot_bot.py
   pip install "steeper[ptb]"     && python examples/ptb_bot.py
   ```

Send `/start` to your bot; the message (and the bot's reply) should appear in Steeper.
