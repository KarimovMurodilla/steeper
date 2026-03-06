from src.integrations.telegram.bot.telegram_bot_api import TelegramBotAPIService


def get_telegram_bot_api_service() -> TelegramBotAPIService:
    return TelegramBotAPIService()
