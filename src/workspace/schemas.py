from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.core.schemas import Base
from src.user.schemas import UserSummaryViewModel
from src.workspace.enums import WorkspaceRole


class WorkspaceCreateRequest(Base):
    """Schema for creating a new workspace."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Company or Team name",
        examples=["Acme Corp"],
    )


class WorkspaceUpdateRequest(Base):
    """Schema for updating workspace details."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="New workspace name",
        examples=["Global Corp"],
    )


class InviteMemberRequest(Base):
    """Schema for inviting a user to the workspace."""

    telegram_id: int = Field(
        ..., description="Telegram ID of the user to invite", examples=[123456789]
    )
    role: WorkspaceRole = Field(
        default=WorkspaceRole.MEMBER,
        description="Role in the workspace (owner/member)",
        examples=[WorkspaceRole.MEMBER],
    )


class UpdateMemberRoleRequest(Base):
    """Schema for changing a member's role."""

    role: WorkspaceRole = Field(
        ..., description="New role to assign", examples=[WorkspaceRole.OWNER]
    )


class WorkspaceViewModel(Base):
    """
    Public view model for a Workspace.
    Does not include the list of members to keep the response light.
    """

    id: UUID = Field(
        ...,
        description="Workspace ID",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    name: str = Field(..., description="Workspace name", examples=["Acme Corp"])
    created_at: datetime = Field(
        ..., description="Creation date", examples=["2025-01-01T12:00:00Z"]
    )
    updated_at: datetime | None = Field(
        None, description="Last update date", examples=["2025-01-02T12:00:00Z"]
    )


class WorkspaceMemberViewModel(Base):
    """
    View model representing a user inside a workspace context.
    Includes the nested User summary and their specific role in this workspace.
    """

    role: WorkspaceRole = Field(
        ..., description="User's role in the workspace", examples=[WorkspaceRole.MEMBER]
    )
    user: UserSummaryViewModel = Field(..., description="User summary information")


class InviteSuccessResponse(Base):
    """Response returned by POST /workspaces/invite."""

    success: bool = Field(
        True, description="Indicates successful invitation", examples=[True]
    )


class WorkspaceInviteEmailBody(Base):
    """Template context for the workspace_invite.html email."""

    title: str = Field(..., description="Email title")
    name: str = Field(..., description="Invitee's name")
    workspace_name: str = Field(..., description="Workspace name")
    role: str = Field(..., description="Assigned role")
    link: str = Field(..., description="Invitation link")
