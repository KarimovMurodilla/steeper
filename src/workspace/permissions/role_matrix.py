from src.workspace.enums import WorkspaceRole
from src.workspace.permissions.enum import WorkspacePermission


WORKSPACE_ROLE_PERMISSIONS: dict[WorkspaceRole, set[WorkspacePermission]] = {
    WorkspaceRole.OWNER: {
        WorkspacePermission.VIEW_DASHBOARD,
        WorkspacePermission.VIEW_MEMBERS,
        WorkspacePermission.INVITE_MEMBER,
        WorkspacePermission.EDIT_MEMBER_ROLE,
        WorkspacePermission.REMOVE_MEMBER,
        WorkspacePermission.VIEW_BILLING,
        WorkspacePermission.MANAGE_SUBSCRIPTION,
        WorkspacePermission.DOWNLOAD_INVOICES,
        WorkspacePermission.CREATE_BOT,
        WorkspacePermission.DELETE_BOT,
        WorkspacePermission.EDIT_WORKSPACE_SETTINGS,
        WorkspacePermission.DELETE_WORKSPACE,
    },
    WorkspaceRole.MEMBER: {
        WorkspacePermission.VIEW_DASHBOARD,
        WorkspacePermission.VIEW_MEMBERS,
    },
}
