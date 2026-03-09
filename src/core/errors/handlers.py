from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import sentry_sdk
from starlette.responses import Response

from loggers import get_logger
from src.core.errors.exceptions import (
    CoreException,
    FilteringError,
    InfrastructureException,
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
    InstanceProcessingException,
    PayloadTooLargeException,
    TooManyRequestsException,
)
from src.core.i18n.enums import LanguageType
from src.core.i18n.errors.en import ERROR_TEXTS_EN
from src.core.i18n.errors.ru import ERROR_TEXTS_RU
from src.core.i18n.errors.uz import ERROR_TEXTS_UZ
from src.core.i18n.utils import parse_language

response_logger = get_logger("app.request.error_response", plain_format=True)

# Type for exception handler
ExcType = TypeVar("ExcType", bound=Exception)
HandlerCallable = Callable[[Request, Exception], Awaitable[Response]]
_I18N_ERRORS_MAP = {
    LanguageType.RU: ERROR_TEXTS_RU,
    LanguageType.UZ: ERROR_TEXTS_UZ,
    LanguageType.EN: ERROR_TEXTS_EN,
}


def as_exception_handler(handler: Any) -> HandlerCallable:
    """
    Convert a handler class instance to a compatible exception handler callable.
    This helps mypy understand the correct typing for FastAPI exception handlers.

    Args:
        handler: An instance of an exception handler class with __call__ method

    Returns:
        A callable with the correct type signature for FastAPI exception handlers
    """
    return cast(HandlerCallable, handler.__call__)


def mask_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """Helper to mask sensitive keys in dictionaries."""
    sensitive_keys = {
        "authorization",
        "token",
        "password",
        "secret",
        "api_key",
        "api-key",
        "access_token",
    }
    masked = {}
    for k, v in data.items():
        if k.lower() in sensitive_keys:
            masked[k] = "***"
        else:
            masked[k] = v
    return masked


def format_error_response(code: str, message: str) -> dict[str, Any]:
    """
    Format error response content for JSONResponse

    Args:
        code: Type of error (e.g., "Unauthorized", "Instance not found")
        message: Detailed error message

    Returns:
        Dictionary with error information
    """
    return {"error": {"code": code, "message": message}}


def format_log_message(
    request: Request,
    exc: Exception,
    include_request_path: bool = False,
) -> str:
    """
    Format error message for logging with support for CoreException,
    ValidationErrors, and standard Python Exceptions.
    """
    request_id = request.headers.get("x-request-id") or getattr(
        getattr(request, "state", object()), "request_id", None
    )
    prefix = f"[{request_id}] " if request_id else ""

    code = "internal_error"
    params: dict[str, Any] = {}
    dev_info: dict[str, Any] = {}
    raw_message = ""

    if isinstance(exc, CoreException):
        code = exc.code or "core_error"
        params = exc.params or {}
        dev_info = exc.additional_info or {}

    elif isinstance(exc, (RequestValidationError, ValidationError)):
        code = "validation_error"
        dev_info = {"validation_errors": exc.errors()}

    else:
        code = exc.__class__.__name__
        raw_message = str(exc)

    log_msg = f"{prefix}[{code}]"

    if include_request_path:
        endpoint = request.url.path
        method = request.method
        log_msg = f"{prefix}[{code}] {method} {endpoint}"

    if raw_message:
        log_msg += f" | Msg: {raw_message}"

    if params:
        safe_params = mask_sensitive_data(params)
        log_msg += f" | Params: {safe_params}"

    if dev_info:
        safe_info = (
            mask_sensitive_data(dev_info) if isinstance(dev_info, dict) else dev_info
        )
        log_msg += f" | DevInfo: {safe_info}"

    return log_msg


# ----- I18n Handler Mixin -----
class I18nExceptionHandlerMixin:
    def get_localized_message(self, request: Request, exc: CoreException) -> str:
        accept_language = request.headers.get("Accept-Language")
        language = parse_language(accept_language)

        translations = _I18N_ERRORS_MAP.get(language, ERROR_TEXTS_RU)
        template = translations.get(exc.code, str(exc.code))

        safe_params = defaultdict(str, exc.params)
        try:
            return template.format(**safe_params)
        except Exception:
            return template


# ----- Infrastructure error handler ----- #
class InfrastructureExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(
        self, request: Request, exc: InfrastructureException
    ) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.error(log_msg)

        message = self.get_localized_message(request, exc)

        sentry_sdk.capture_exception(exc)
        return JSONResponse(
            status_code=500,
            content=format_error_response(exc.code, message),
        )


# ----- Validation Handlers ----- #
class RequestValidationExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(
        self, request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        safe_detail = jsonable_encoder(exc.errors())
        log_msg = format_log_message(request, exc, include_request_path=True)
        response_logger.debug(log_msg)
        return JSONResponse(status_code=422, content={"detail": safe_detail})


class ValidationErrorExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(self, request: Request, exc: ValidationError) -> JSONResponse:
        log_msg = format_log_message(request, exc, include_request_path=True)
        response_logger.error(log_msg)
        sentry_sdk.capture_exception(exc)
        return JSONResponse(status_code=500, content={"detail": "Unexpected error"})


# ----- Core Error Handlers ----- #
class CoreExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(self, request: Request, exc: CoreException) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.info(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=400,
            content=format_error_response(exc.code, message),
        )


class InstanceNotFoundExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(
        self, request: Request, exc: InstanceNotFoundException
    ) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.info(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=404,
            content=format_error_response(exc.code, message),
        )


class InstanceAlreadyExistsExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(
        self, request: Request, exc: InstanceAlreadyExistsException
    ) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.info(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=409,
            content=format_error_response(exc.code, message),
        )


class InstanceProcessingExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(
        self, request: Request, exc: InstanceProcessingException
    ) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.info(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=400,
            content=format_error_response(exc.code, message),
        )


class PayloadTooLargeExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(
        self, request: Request, exc: PayloadTooLargeException
    ) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.info(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=413,
            content=format_error_response(exc.code, message),
        )


class FilteringErrorHandler(I18nExceptionHandlerMixin):
    async def __call__(self, request: Request, exc: FilteringError) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.warning(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=400,
            content=format_error_response(exc.code, message),
        )


class UnauthorizedExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(self, request: Request, exc: CoreException) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.warning(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=401,
            content=format_error_response(exc.code, message),
        )


class AccessForbiddenExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(self, request: Request, exc: CoreException) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.warning(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=403,
            content=format_error_response(exc.code, message),
        )


class NotAcceptableExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(self, request: Request, exc: CoreException) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.info(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=406,
            content=format_error_response(exc.code, message),
        )


class PermissionDeniedExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(self, request: Request, exc: CoreException) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.warning(log_msg)

        message = self.get_localized_message(request, exc)

        return JSONResponse(
            status_code=403,
            content=format_error_response(exc.code, message),
        )


class TooManyRequestsExceptionHandler(I18nExceptionHandlerMixin):
    async def __call__(
        self, request: Request, exc: TooManyRequestsException
    ) -> JSONResponse:
        log_msg = format_log_message(request, exc)
        response_logger.info(log_msg)

        message = self.get_localized_message(request, exc)

        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)

        return JSONResponse(
            status_code=429,
            content=format_error_response(exc.code, message),
            headers=headers,
        )
