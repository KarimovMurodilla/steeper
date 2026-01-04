from enum import StrEnum


class WorkspacePermission(StrEnum):
    """
    Permissions related to managing a Workspace resource.
    Checked against WorkspaceMember role (Owner/Member).
    """
    
    # Dashboard & Analytics
    VIEW_DASHBOARD = "workspace:view_dashboard"

    # Team Management
    VIEW_MEMBERS = "workspace:view_members"
    INVITE_MEMBER = "workspace:invite_member"
    EDIT_MEMBER_ROLE = "workspace:edit_member_role"
    REMOVE_MEMBER = "workspace:remove_member"

    # Billing & Subscription
    VIEW_BILLING = "workspace:view_billing"
    MANAGE_SUBSCRIPTION = "workspace:manage_subscription"
    DOWNLOAD_INVOICES = "workspace:download_invoices"

    # Bot Management (Creation/Deletion)
    # Note: Using bots is handled by BotPermission, but creating them is a Workspace action.
    CREATE_BOT = "workspace:create_bot"
    DELETE_BOT = "workspace:delete_bot"

    # Workspace Settings
    EDIT_WORKSPACE_SETTINGS = "workspace:edit_settings"
    DELETE_WORKSPACE = "workspace:delete_workspace"
