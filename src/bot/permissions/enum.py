from enum import StrEnum


class BotPermission(StrEnum):
    """
    Enumeration of granular permissions within the Bot context.
    These permissions control access to specific features of a bot.
    """

    # --- Dashboard & Analytics ---
    VIEW_DASHBOARD = "bot:view_dashboard"
    VIEW_ANALYTICS = "bot:view_analytics"
    EXPORT_DATA = "bot:export_data"

    # --- Communication (Chats) ---
    VIEW_CHATS = "bot:view_chats"
    SEND_MESSAGES = "bot:send_messages"
    DELETE_MESSAGES = "bot:delete_messages"
    MANAGE_TAGS = "bot:manage_tags"

    # --- Marketing (Broadcasts) ---
    VIEW_BROADCASTS = "bot:view_broadcasts"
    CREATE_BROADCAST = "bot:create_broadcast"
    EDIT_BROADCAST = "bot:edit_broadcast"
    # Approve allows launching the broadcast (high-level action)
    APPROVE_BROADCAST = "bot:approve_broadcast"
    DELETE_BROADCAST = "bot:delete_broadcast"

    # --- Audience (CRM) ---
    VIEW_AUDIENCE = "bot:view_audience"
    EDIT_AUDIENCE = "bot:edit_audience"

    # --- Bot Settings & Administration ---
    VIEW_SETTINGS = "bot:view_settings"
    EDIT_SETTINGS = "bot:edit_settings"  # Token, Name, Webhook
    MANAGE_ROLES = "bot:manage_roles"  # Invite other admins to this bot
