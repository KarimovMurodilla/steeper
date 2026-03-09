from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from src.core.redis.cache.lifecycle import (
    on_redis_cache_shutdown,
    on_redis_cache_startup,
)
from src.core.redis.lifecycle import on_redis_shutdown, on_redis_startup
from src.main.config import config
from src.main.sentry import init_sentry
from src.realtime.broker import broker as realtime_broker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    init_sentry()
    await on_redis_startup(app, config.redis.dsn)

    await on_redis_cache_startup()

    # Start FastStream RabbitMQ broker (enables realtime event consumers)
    await realtime_broker.start()
    logger.info("FastStream RabbitBroker started")

    yield

    # Shutdown FastStream broker gracefully
    await realtime_broker.stop()
    logger.info("FastStream RabbitBroker stopped")

    await on_redis_cache_shutdown()
    await on_redis_shutdown(app)
