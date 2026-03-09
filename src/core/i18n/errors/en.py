from src.core.errors.enums import ErrorCode

ERROR_TEXTS_EN: dict[ErrorCode, str] = {
    # --- General / Server ---
    ErrorCode.INTERNAL_SERVER_ERROR: "Internal server error.",
    # --- Authentication & Authorization ---
    ErrorCode.AUTH_INVALID_CREDENTIALS: "Invalid email or password.",
    ErrorCode.AUTH_COULD_NOT_VALIDATE: "Could not validate credentials.",
    ErrorCode.AUTH_TOKEN_EXPIRED: "Token has expired.",
    ErrorCode.AUTH_TOKEN_INVALID: "Invalid token.",
    ErrorCode.AUTH_TOKEN_INVALID_STRUCTURE: "Invalid token structure.",
    ErrorCode.AUTH_TOKEN_NOT_FOUND: "Authentication token not found.",
    ErrorCode.AUTH_INVALID_OR_EXPIRED_TOKEN: "Invalid or expired token.",
    # --- User ---
    ErrorCode.USER_NOT_FOUND: "User not found.",
    ErrorCode.USER_BLOCKED: "User is blocked.",
    # --- General ---
    ErrorCode.GENERAL_NOT_FOUND: "Resource not found.",
    ErrorCode.GENERAL_DATE_FUTURE: "Cannot fetch information for future dates.",
    # --- Infrastructure ---
    ErrorCode.SYSTEM_HEALTH_CHECK_FAILED: "System health check failed.",
    # --- Workspace ---
    ErrorCode.WORKSPACE_NOT_FOUND: "Workspace not found.",
    ErrorCode.WORKSPACE_ACCESS_DENIED: "Workspace not found or access denied.",
    ErrorCode.WORKSPACE_NOT_OWNER: "User is not the owner of the workspace.",
    ErrorCode.WORKSPACE_ALREADY_MEMBER: "User is already a member of this workspace.",
    ErrorCode.WORKSPACE_MEMBER_NOT_FOUND: "User is not a member of the workspace.",
    # --- Bot ---
    ErrorCode.BOT_NOT_FOUND: "Bot not found.",
    ErrorCode.BOT_UPDATE_FAILED: "Failed to update bot information with Telegram.",
    ErrorCode.BOT_REGISTRATION_FAILED: "Failed to register bot with Telegram.",
    ErrorCode.BOT_ADMIN_ALREADY_EXISTS: "User is already an admin of this bot.",
    # --- Marketing ---
    ErrorCode.BROADCAST_NOT_FOUND: "Broadcast not found.",
    ErrorCode.BROADCAST_ALREADY_LAUNCHED: "Broadcast already launched.",
    ErrorCode.CAMPAIGN_NOT_FOUND: "Campaign not found.",
    # --- Communication ---
    ErrorCode.CHAT_NOT_FOUND: "Chat not found.",
    ErrorCode.MESSAGE_SEND_FAILED: "Failed to send message.",
    # --- Auth Additional ---
    ErrorCode.AUTH_NOT_AUTHENTICATED: "Not authenticated.",
    ErrorCode.AUTH_ACCESS_FORBIDDEN: "Access forbidden.",
    ErrorCode.AUTH_PERMISSION_DENIED: "User does not have required permissions.",
    ErrorCode.AUTH_REFRESH_TOKEN_NOT_OWNED: "Refresh token does not belong to the user.",
    ErrorCode.AUTH_TOKEN_POTENTIAL_REUSE: "Token has been invalidated due to potential reuse.",
    ErrorCode.AUTH_TOKEN_REUSE_DETECTED: "Token reuse detected. All sessions invalidated.",
    ErrorCode.AUTH_TELEGRAM_HASH_MISMATCH: "Telegram authentication hash mismatch.",
    ErrorCode.AUTH_TELEGRAM_DATA_OUTDATED: "Telegram authentication data is outdated.",
    ErrorCode.AUTH_TELEGRAM_USER_NOT_FOUND: "Telegram user not found in data.",
    ErrorCode.AUTH_TELEGRAM_DATA_REQUIRED: "Telegram authentication data is required.",
}
