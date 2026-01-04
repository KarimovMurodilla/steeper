from enum import StrEnum


class PlatformPermission(StrEnum):
    """
    Global Permissions for the User entity and Platform Administration.
    Checked against User.is_superuser or basic authentication.
    """

    # Superuser / Platform Admin (Steeper Staff)
    # These grant access to the "God Mode" admin panel
    VIEW_SYSTEM_LOGS = "system:view_logs"
    MANAGE_PLATFORM_SETTINGS = "system:manage_platform_settings"
    BLOCK_USER = "system:block_user"
    VIEW_ALL_WORKSPACES = "system:view_all_workspaces"
