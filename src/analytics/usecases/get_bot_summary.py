"""Use case: return analytics summary for a single bot."""

from uuid import UUID

from src.analytics.schemas import BotAnalyticsSummary
from src.core.database.uow.abstract import RepositoryProtocol
from src.core.database.uow.application import ApplicationUnitOfWork


class GetBotAnalyticsSummaryUseCase:
    """
    Aggregates key metrics for a bot in a single round-trip.

    Metrics:
      - users:    total unique Telegram users
      - chats:    total chat sessions
      - messages: total messages across all chats
      - dau:      distinct users who had any message activity today (UTC)
    """

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, bot_id: UUID) -> BotAnalyticsSummary:
        """
        Executes the business logic for getting bot analytics summary.

        Args:
            bot_id (UUID): The unique identifier of the bot.

        Returns:
            BotAnalyticsSummary: Analytics summary object.
        """
        async with self.uow as uow:
            users = await uow.telegram_users.count_by_bot(uow.session, bot_id)
            chats = await uow.chats.count_by_bot(uow.session, bot_id)
            messages = await uow.messages.count_by_bot(uow.session, bot_id)
            dau = await uow.messages.count_dau_by_bot(uow.session, bot_id)

        return BotAnalyticsSummary(
            users=users,
            chats=chats,
            messages=messages,
            dau=dau,
        )
