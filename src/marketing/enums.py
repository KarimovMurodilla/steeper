from enum import StrEnum


class BroadcastStatus(StrEnum):
    DRAFT = "draft"  # Draft, being edited
    SCHEDULED = "scheduled"  # Scheduled for future
    PROCESSING = "processing"  # In progress of sending (worker is running)
    SENT = "sent"  # Completely finished
    FAILED = "failed"  # Finished with errors (or cancelled)
    CANCELLED = "cancelled"  # Cancelled by user

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}


class DeliveryStatus(StrEnum):
    PENDING = "pending"  # In queue
    SUCCESS = "success"  # Delivered (API returned 200 OK)
    FAILED = "failed"  # Error (403 Forbidden, etc.)
    SKIPPED = "skipped"  # Skipped (e.g., user banned the bot)

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}
