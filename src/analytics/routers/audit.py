"""Audit log router — mounted under /v1/audit-logs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.repositories import AuditLogRepository
from src.analytics.schemas import AuditLogListItemViewModel
from src.core.database.session import get_session
from src.core.pagination import (
    PaginatedResponse,
    PaginationParams,
    make_paginated_response,
)
from src.workspace.permissions.checker import require_workspace_permission
from src.workspace.permissions.enum import WorkspacePermission

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[AuditLogListItemViewModel],
    status_code=status.HTTP_200_OK,
)
async def list_audit_logs(
    pagination: Annotated[PaginationParams, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[
        None, Depends(require_workspace_permission(WorkspacePermission.VIEW_DASHBOARD))
    ],
    bot_id: UUID | None = Query(default=None, description="Filter by bot"),
) -> PaginatedResponse[AuditLogListItemViewModel]:
    """
    Paginated audit log. Requires VIEW_DASHBOARD workspace permission.
    Optionally filter by bot_id.
    """
    repo = AuditLogRepository()
    rows, total = await repo.get_paginated_with_actor(
        session, page=pagination.page, size=pagination.size, bot_id=bot_id
    )
    items = [
        AuditLogListItemViewModel(
            actor=str(telegram_id),
            action=log.action_type,
            created_at=log.created_at,
        )
        for log, telegram_id in rows
    ]
    return make_paginated_response(items=items, total=total, pagination=pagination)
