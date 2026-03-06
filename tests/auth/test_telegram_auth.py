from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.errors.exceptions import (
    PermissionDeniedException,
    UnauthorizedException,
)
from src.user.auth.schemas import (
    TelegramAuthRequest,
    TelegramAuthSource,
    TelegramLoginWidgetSchema,
)
from src.user.auth.strategies.telegram.dto import TelegramUserData
from src.user.auth.strategies.telegram.webapp import WebAppAuthStrategy
from src.user.auth.strategies.telegram.widget import LoginWidgetAuthStrategy
from src.user.auth.usecases.telegram_auth import TelegramAuthUseCase
from src.user.models import User


@pytest.fixture
def uow_mock() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None
    return uow


@pytest.fixture
def redis_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.exists.return_value = True
    mock.eval.return_value = "OK"
    mock.set.return_value = None
    mock.expire.return_value = None
    return mock


@pytest.mark.asyncio
async def test_telegram_auth_webapp_success(
    uow_mock: AsyncMock,
    redis_mock: AsyncMock,
) -> None:
    telegram_id = 999111222
    mock_user = User(id=str(uuid4()), telegram_id=telegram_id, is_active=True)
    uow_mock.users.get_single.return_value = mock_user

    webapp_strategy = WebAppAuthStrategy()
    webapp_strategy.verify = MagicMock(
        return_value=TelegramUserData(
            telegram_id=telegram_id,
            first_name="Test",
            last_name=None,
            username="test_user",
            photo_url=None,
            language_code=None,
        )
    )

    use_case = TelegramAuthUseCase(
        uow_mock, redis_mock, {TelegramAuthSource.WEBAPP: webapp_strategy}
    )

    req = TelegramAuthRequest(source=TelegramAuthSource.WEBAPP, init_data="mock_data")
    result = await use_case.execute(req)

    assert result.user.telegram_id == telegram_id
    assert result.tokens.access_token is not None
    assert result.tokens.refresh_token is not None


@pytest.mark.asyncio
async def test_telegram_auth_widget_no_workspace(
    uow_mock: AsyncMock,
    redis_mock: AsyncMock,
) -> None:
    telegram_id = 888111222
    mock_user = User(id=str(uuid4()), telegram_id=telegram_id, is_active=True)
    uow_mock.users.get_single.return_value = mock_user
    uow_mock.workspace_members.exists.return_value = False

    widget_strategy = LoginWidgetAuthStrategy()
    widget_strategy.verify = MagicMock(
        return_value=TelegramUserData(
            telegram_id=telegram_id,
            first_name="Test",
            last_name=None,
            username="test_user",
            photo_url=None,
            language_code=None,
        )
    )

    use_case = TelegramAuthUseCase(
        uow_mock, redis_mock, {TelegramAuthSource.LOGIN_WIDGET: widget_strategy}
    )

    req = TelegramAuthRequest(
        source=TelegramAuthSource.LOGIN_WIDGET,
        telegram_login=TelegramLoginWidgetSchema(
            id=telegram_id, first_name="Test", auth_date=123, hash="fake"
        ),
    )

    with pytest.raises(PermissionDeniedException) as exc:
        await use_case.execute(req)

    assert exc.value.message == "USER_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_telegram_auth_widget_success(
    uow_mock: AsyncMock,
    redis_mock: AsyncMock,
) -> None:
    telegram_id = 777111222
    mock_user = User(id=str(uuid4()), telegram_id=telegram_id, is_active=True)
    uow_mock.users.get_single.return_value = mock_user
    uow_mock.workspace_members.exists.return_value = True

    widget_strategy = LoginWidgetAuthStrategy()
    widget_strategy.verify = MagicMock(
        return_value=TelegramUserData(
            telegram_id=telegram_id,
            first_name="Test",
            last_name=None,
            username="test_user",
            photo_url=None,
            language_code=None,
        )
    )

    use_case = TelegramAuthUseCase(
        uow_mock, redis_mock, {TelegramAuthSource.LOGIN_WIDGET: widget_strategy}
    )

    req = TelegramAuthRequest(
        source=TelegramAuthSource.LOGIN_WIDGET,
        telegram_login=TelegramLoginWidgetSchema(
            id=telegram_id, first_name="Test", auth_date=123, hash="fake"
        ),
    )

    result = await use_case.execute(req)

    assert result.user.telegram_id == telegram_id
    assert result.tokens.access_token is not None
    assert result.tokens.refresh_token is not None


@pytest.mark.asyncio
async def test_telegram_auth_invalid_signature(
    uow_mock: AsyncMock,
    redis_mock: AsyncMock,
) -> None:
    webapp_strategy = WebAppAuthStrategy()
    use_case = TelegramAuthUseCase(
        uow_mock, redis_mock, {TelegramAuthSource.WEBAPP: webapp_strategy}
    )

    req = TelegramAuthRequest(source=TelegramAuthSource.WEBAPP, init_data="wrong_data")

    with pytest.raises(UnauthorizedException) as exc:
        await use_case.execute(req)

    assert exc.value.message == "INVALID_TELEGRAM_SIGNATURE"
