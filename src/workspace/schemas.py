from pydantic import Field

from src.core.schemas import IDSchema, TimestampSchema


class WorkspaceBase(IDSchema, TimestampSchema):
    name: str = Field(..., min_length=1, max_length=100)
    is_active: bool


class WorkspaceRead(WorkspaceBase):
    pass


class WorkspaceCreate(IDSchema):
    name: str = Field(..., min_length=1, max_length=100)


class WorkspaceUpdate(IDSchema):
    name: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None
