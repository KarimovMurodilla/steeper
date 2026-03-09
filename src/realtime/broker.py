from faststream.rabbit import RabbitBroker, RabbitExchange
from faststream.rabbit.schemas import ExchangeType

from loggers import get_logger
from src.main.config import config

logger = get_logger(__name__)

broker = RabbitBroker(config.rabbitmq.dsn)

steeper_exchange = RabbitExchange(
    name="steeper.events",
    type=ExchangeType.TOPIC,
    durable=True,
)


def get_broker() -> RabbitBroker:
    """Return the module-level FastStream RabbitBroker instance."""
    return broker
