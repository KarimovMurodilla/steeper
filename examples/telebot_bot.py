"""Minimal pyTelegramBotAPI (telebot) bot wired to Steeper.

Run:
    pip install steeper[telebot]
    export BOT_TOKEN=...        # from BotFather
    export STEEPER_BOT_ID=...   # UUID of the bot registered in Steeper
    export STEEPER_BASE_URL=http://localhost:8000
    python examples/telebot_bot.py
"""

import os

import telebot

from steeper.integrations.telebot import SteeperMiddleware

BOT_TOKEN = os.environ["BOT_TOKEN"]
STEEPER_BOT_ID = os.environ["STEEPER_BOT_ID"]
STEEPER_BASE_URL = os.environ.get("STEEPER_BASE_URL", "http://localhost:8000")

bot = telebot.TeleBot(BOT_TOKEN)

SteeperMiddleware(
    base_url=STEEPER_BASE_URL,
    bot_id=STEEPER_BOT_ID,
    bot_token=BOT_TOKEN,
).setup(bot)


@bot.message_handler(commands=["start"])
def cmd_start(message: telebot.types.Message) -> None:
    bot.reply_to(message, "Hello from a Steeper-synced bot!")


if __name__ == "__main__":
    bot.polling()
