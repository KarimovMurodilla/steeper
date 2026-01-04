from enum import StrEnum


class BotRole(StrEnum):
    ADMIN = "admin"  # Full access to the bot (tokens, settings, deletion)
    EDITOR = "editor"  # Content: broadcasts, buttons (but not bot settings)
    SUPPORT = "support"  # Operator: only replying in chats
    VIEWER = "viewer"  # Analyst: read-only access to statistics

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}


class BotStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}
