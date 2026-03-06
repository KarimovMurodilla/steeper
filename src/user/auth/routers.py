from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.limiter.depends import RateLimiter
from src.core.schemas import TokenModel
from src.user.auth.dependencies import (
    get_access_by_refresh_token,
    get_user_id_from_token,
)
from src.user.auth.jwt_payload_schema import JWTPayload
from src.user.auth.schemas import (
    TelegramAuthRequest,
    TelegramAuthResponse,
)
from src.user.auth.usecases.get_access_by_refresh import (
    GetTokensByRefreshUserUseCase,
    get_tokens_by_refresh_user_use_case,
)
from src.user.auth.usecases.telegram_auth import (
    TelegramAuthUseCase,
    get_telegram_auth_use_case,
)
from src.user.models import User

router = APIRouter()


@router.post(
    "/telegram",
    status_code=200,
    response_model=TelegramAuthResponse,
    dependencies=[Depends(RateLimiter(times=10, minutes=10))],
)
async def authenticate_via_telegram(
    data: TelegramAuthRequest,
    use_case: Annotated[TelegramAuthUseCase, Depends(get_telegram_auth_use_case)],
) -> TelegramAuthResponse:
    """
    Authenticate user via Telegram WebApp or Login Widget.
    """
    return await use_case.execute(data=data)


@router.post(
    "/login/refresh",
    response_model=TokenModel,
    dependencies=[
        Depends(  # IP-based rate limiting
            RateLimiter(
                times=20,
                minutes=15,
            )
        ),
        Depends(  # User-based rate limiting
            RateLimiter(
                times=5,
                minutes=15,
                identifier=get_user_id_from_token,
            )
        ),
    ],
)
async def get_access_by_refresh(
    user_and_payload: Annotated[
        tuple[User, JWTPayload], Depends(get_access_by_refresh_token)
    ],
    use_case: Annotated[
        GetTokensByRefreshUserUseCase, Depends(get_tokens_by_refresh_user_use_case)
    ],
) -> TokenModel:
    """
    Refresh the access token using a valid refresh token.
    """
    current_user, old_payload = user_and_payload

    return await use_case.execute(user=current_user, old_token_payload=old_payload)
