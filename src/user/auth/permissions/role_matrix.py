from src.user.auth.permissions.enum import SystemPermission
from src.user.enums import SystemRole

SYSTEM_ROLE_PERMISSIONS: dict[SystemRole, set[SystemPermission]] = {
    SystemRole.OWNER: {
        SystemPermission.MANAGE_BILLING,
        SystemPermission.MANAGE_MEMBERS,
        SystemPermission.CREATE_BOT,
        SystemPermission.DELETE_BOT,
    },
    SystemRole.MEMBER: set(),
}
