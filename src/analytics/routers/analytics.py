"""Analytics summary router — mounted under /v1/bots."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.analytics.dependencies import get_bot_analytics_summary_use_case
from src.analytics.schemas import BotAnalyticsSummary
from src.analytics.usecases.get_bot_summary import GetBotAnalyticsSummaryUseCase
from src.bot.enums import BotRole
from src.bot.permissions.checker import require_bot_permission
from src.bot.permissions.enum import BotPermission

router = APIRouter()


@router.get(
    "/{bot_id}/analytics/summary",
    response_model=BotAnalyticsSummary,
    status_code=status.HTTP_200_OK,
)
async def get_bot_analytics_summary(
    bot_id: UUID,
    use_case: Annotated[
        GetBotAnalyticsSummaryUseCase,
        Depends(get_bot_analytics_summary_use_case),
    ],
    _: Annotated[
        BotRole,
        Depends(require_bot_permission(BotPermission.VIEW_DASHBOARD)),
    ],
) -> BotAnalyticsSummary:
    """
    Bot analytics summary: users, chats, messages, and daily active users.
    Requires VIEW_DASHBOARD bot permission.
    """
    return await use_case.execute(bot_id=bot_id)
