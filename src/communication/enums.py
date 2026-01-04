from enum import StrEnum


class ChatStatus(StrEnum):
    OPEN = "open"  # Chat is active, bot/admin can respond
    CLOSED = "closed"  # Chat is closed (archived)
    BLOCKED = "blocked"  # User has blocked the bot

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}


class SenderType(StrEnum):
    USER = "user"  # Regular Telegram user
    BOT = "bot"  # Bot auto-reply
    ADMIN = "admin"  # Operator/admin response via dashboard
    SYSTEM = "system"  # System notification

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}


class MessageType(StrEnum):
    TEXT = "text"
    MEDIA = "media"  # Temporary general type for media messages
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    SYSTEM = "system"  # Service message (e.g., "Chat closed")

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}
