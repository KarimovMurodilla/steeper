from enum import StrEnum


class WorkspaceRole(StrEnum):
    OWNER = "owner"  # Owner: pays for the service, creates bots, deletes workspace
    MEMBER = "member"  # Member: has no permissions until granted access to resources

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}
