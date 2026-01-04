from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from src.core.schemas import Base
from src.workspace.enums import WorkspaceRole
from src.user.schemas import UserSummaryViewModel


class WorkspaceCreateRequest(Base):
    """Schema for creating a new workspace."""
    name: str = Field(..., min_length=1, max_length=100, description="Company or Team name")


class WorkspaceUpdateRequest(Base):
    """Schema for updating workspace details."""
    name: str | None = Field(None, min_length=1, max_length=100)


class InviteMemberRequest(Base):
    """Schema for inviting a user to the workspace."""
    email: EmailStr = Field(..., description="Email of the user to invite")
    role: WorkspaceRole = Field(default=WorkspaceRole.MEMBER, description="Role in the workspace (owner/member)")


class UpdateMemberRoleRequest(Base):
    """Schema for changing a member's role."""
    role: WorkspaceRole


class WorkspaceViewModel(Base):
    """
    Public view model for a Workspace.
    Does not include the list of members to keep the response light.
    """
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime | None = None


class WorkspaceMemberViewModel(Base):
    """
    View model representing a user inside a workspace context.
    Includes the nested User summary and their specific role in this workspace.
    """
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    joined_at: datetime = Field(alias="created_at")  # Mapping created_at of the link to joined_at
    
    # Nested user details (using existing schema from src.user)
    user: UserSummaryViewModel
