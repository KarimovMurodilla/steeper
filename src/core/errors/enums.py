from enum import StrEnum


class ErrorCode(StrEnum):
    # --- General / Server ---
    INTERNAL_SERVER_ERROR = "internal.server_error"

    # --- Auth ---
    AUTH_INVALID_CREDENTIALS = "auth.invalid_credentials"
    AUTH_COULD_NOT_VALIDATE = "auth.could_not_validate"
    AUTH_TOKEN_EXPIRED = "auth.token_expired"
    AUTH_TOKEN_INVALID = "auth.token_invalid"
    AUTH_TOKEN_INVALID_STRUCTURE = "auth.token_invalid_structure"
    AUTH_TOKEN_NOT_FOUND = "auth.token_not_found"
    AUTH_INVALID_OR_EXPIRED_TOKEN = "auth.invalid_or_expired_token"

    # --- User ---
    USER_NOT_FOUND = "user.not_found"
    USER_BLOCKED = "user.blocked"

    # --- General ---
    GENERAL_NOT_FOUND = "general.not_found"
    GENERAL_DATE_FUTURE = "general.date_future"

    # --- Infrastructure / System ---
    SYSTEM_HEALTH_CHECK_FAILED = "system.health_check_failed"

    # --- Workspace ---
    WORKSPACE_NOT_FOUND = "workspace.not_found"
    WORKSPACE_ACCESS_DENIED = "workspace.access_denied"
    WORKSPACE_NOT_OWNER = "workspace.not_owner"
    WORKSPACE_ALREADY_MEMBER = "workspace.already_member"
    WORKSPACE_MEMBER_NOT_FOUND = "workspace.member_not_found"

    # --- Bot ---
    BOT_NOT_FOUND = "bot.not_found"
    BOT_UPDATE_FAILED = "bot.update_failed"
    BOT_REGISTRATION_FAILED = "bot.registration_failed"
    BOT_ADMIN_ALREADY_EXISTS = "bot.admin_already_exists"

    # --- Marketing ---
    BROADCAST_NOT_FOUND = "broadcast.not_found"
    BROADCAST_ALREADY_LAUNCHED = "broadcast.already_launched"
    CAMPAIGN_NOT_FOUND = "campaign.not_found"

    # --- Communication ---
    CHAT_NOT_FOUND = "chat.not_found"
    MESSAGE_SEND_FAILED = "message.send_failed"

    # --- Auth Additional ---
    AUTH_NOT_AUTHENTICATED = "auth.not_authenticated"
    AUTH_ACCESS_FORBIDDEN = "auth.access_forbidden"
    AUTH_PERMISSION_DENIED = "auth.permission_denied"
    AUTH_REFRESH_TOKEN_NOT_OWNED = "auth.refresh_token_not_owned"
    AUTH_TOKEN_POTENTIAL_REUSE = "auth.token_potential_reuse"
    AUTH_TOKEN_REUSE_DETECTED = "auth.token_reuse_detected"
    AUTH_TELEGRAM_HASH_MISMATCH = "auth.telegram_hash_mismatch"
    AUTH_TELEGRAM_DATA_OUTDATED = "auth.telegram_data_outdated"
    AUTH_TELEGRAM_USER_NOT_FOUND = "auth.telegram_user_not_found"
    AUTH_TELEGRAM_DATA_REQUIRED = "auth.telegram_data_required"
