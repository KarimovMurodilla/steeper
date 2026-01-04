from enum import StrEnum


class SystemPermission(StrEnum):
    # --- WORKSPACE / GLOBAL PERMISSIONS ---
    MANAGE_BILLING = "workspace:manage_billing"
    MANAGE_MEMBERS = "workspace:manage_members"
    CREATE_BOT = "workspace:create_bot"
    DELETE_BOT = "workspace:delete_bot"
