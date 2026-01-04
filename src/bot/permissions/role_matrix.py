from src.bot.enums import BotRole
from src.bot.permissions.enum import BotPermission

# Matrix defining which permissions constitute each BotRole.
BOT_ROLE_PERMISSIONS: dict[BotRole, set[BotPermission]] = {
    BotRole.ADMIN: {
        BotPermission.VIEW_DASHBOARD,
        BotPermission.VIEW_ANALYTICS,
        BotPermission.EXPORT_DATA,
        BotPermission.VIEW_CHATS,
        BotPermission.SEND_MESSAGES,
        BotPermission.DELETE_MESSAGES,
        BotPermission.MANAGE_TAGS,
        BotPermission.VIEW_BROADCASTS,
        BotPermission.CREATE_BROADCAST,
        BotPermission.EDIT_BROADCAST,
        BotPermission.APPROVE_BROADCAST,
        BotPermission.DELETE_BROADCAST,
        BotPermission.VIEW_AUDIENCE,
        BotPermission.EDIT_AUDIENCE,
        BotPermission.VIEW_SETTINGS,
        BotPermission.EDIT_SETTINGS,
        BotPermission.MANAGE_ROLES,
    },
    # EDITOR: Can manage content and marketing, but not critical bot settings or roles
    BotRole.EDITOR: {
        BotPermission.VIEW_DASHBOARD,
        BotPermission.VIEW_ANALYTICS,
        BotPermission.VIEW_CHATS,
        BotPermission.SEND_MESSAGES,
        BotPermission.MANAGE_TAGS,
        BotPermission.VIEW_BROADCASTS,
        BotPermission.CREATE_BROADCAST,
        BotPermission.EDIT_BROADCAST,
        # Editors might draft broadcasts, but arguably shouldn't delete or approve them without review
        # (Adjust based on business logic)
        BotPermission.VIEW_AUDIENCE,
        BotPermission.EDIT_AUDIENCE,
        BotPermission.VIEW_SETTINGS,  # View-only settings
    },
    # SUPPORT: Focus on communication with users
    BotRole.SUPPORT: {
        BotPermission.VIEW_DASHBOARD,  # Basic stats
        BotPermission.VIEW_CHATS,
        BotPermission.SEND_MESSAGES,
        BotPermission.MANAGE_TAGS,
        BotPermission.VIEW_AUDIENCE,
    },
    # VIEWER: Read-only access for stakeholders
    BotRole.VIEWER: {
        BotPermission.VIEW_DASHBOARD,
        BotPermission.VIEW_ANALYTICS,
        BotPermission.VIEW_CHATS,
        BotPermission.VIEW_BROADCASTS,
        BotPermission.VIEW_AUDIENCE,
        BotPermission.VIEW_SETTINGS,
    },
}
