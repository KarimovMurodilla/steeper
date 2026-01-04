
from src.bot.models import Bot
from src.bot.repositories.bot import BotRepository
from src.bot.schemas import BotCreateRequest, BotViewModel
from src.core.schemas import Base
from src.core.services import BaseService


class BotService(BaseService[Bot, BotCreateRequest, Base, BotRepository, BotViewModel]):
    def __init__(
        self,
        repository: BotRepository,
    ):
        super().__init__(repository, response_schema=BotViewModel)
