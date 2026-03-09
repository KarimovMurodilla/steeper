import json
import logging

from fastapi import Request
import pytest

from src.core.errors import handlers
from src.core.errors.enums import ErrorCode
from src.core.errors.exceptions import (
    AccessForbiddenException,
    CoreException,
    FilteringError,
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
    InstanceProcessingException,
    NotAcceptableException,
    PermissionDeniedException,
    UnauthorizedException,
)


def _build_request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "http_version": "1.1",
        "scheme": "http",
        "path": "/v1/resource",
        "root_path": "",
        "raw_path": b"/v1/resource",
        "query_string": b"",
        "asgi": {"version": "3.0"},
        "headers": headers or [],
        "client": ("127.0.0.1", 8000),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def _patch_response_logger(monkeypatch: pytest.MonkeyPatch) -> logging.Logger:
    logger = logging.getLogger("response_logger_test")
    logger.handlers = []
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    monkeypatch.setattr(handlers, "response_logger", logger)
    return logger


def test_format_log_message_masks_sensitive_data() -> None:
    request = _build_request(headers=[(b"x-request-id", b"req-123")])

    exc = CoreException(
        code=ErrorCode.AUTH_NOT_AUTHENTICATED,
        params={"token": "secret", "note": "safe"},
        additional_info="token leaked",
    )
    message = handlers.format_log_message(
        request,
        exc,
        include_request_path=True,
    )

    assert "[req-123] [auth.not_authenticated] GET /v1/resource" in message
    assert "'token': '***'" in message
    assert "'note': 'safe'" in message
    assert "token leaked" in message


def test_format_log_message_truncates_long_text() -> None:
    request = _build_request()
    long_message = "a" * 600

    message = handlers.format_log_message(request, Exception(long_message))

    assert message.endswith("...")
    assert message.count("a") == 497


@pytest.mark.asyncio
async def test_core_exception_handler(caplog: pytest.LogCaptureFixture) -> None:
    handler = handlers.CoreExceptionHandler()
    request = _build_request()
    caplog.set_level(logging.INFO, logger="response_logger_test")

    response = await handler(request, CoreException("failed to process"))

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "error": {
            "code": "failed to process",
            "message": "failed to process",
        }
    }
    assert any("failed to process" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_filtering_error_handler_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    handler = handlers.FilteringErrorHandler()
    request = _build_request()
    caplog.set_level(logging.WARNING, logger="response_logger_test")

    response = await handler(request, FilteringError("invalid filter"))

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "error": {
            "code": "invalid filter",
            "message": "invalid filter",
        }
    }
    assert any(
        record.levelno == logging.WARNING and "invalid filter" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "handler_cls,exc_cls,status,error_type,log_level,include_path",
    [
        (
            handlers.InstanceNotFoundExceptionHandler,
            InstanceNotFoundException,
            404,
            "Instance not found",
            logging.INFO,
            False,
        ),
        (
            handlers.InstanceAlreadyExistsExceptionHandler,
            InstanceAlreadyExistsException,
            409,
            "Instance already exists",
            logging.INFO,
            False,
        ),
        (
            handlers.InstanceProcessingExceptionHandler,
            InstanceProcessingException,
            400,
            "Instance processing error",
            logging.INFO,
            False,
        ),
        (
            handlers.UnauthorizedExceptionHandler,
            UnauthorizedException,
            401,
            "Unauthorized",
            logging.WARNING,
            True,
        ),
        (
            handlers.AccessForbiddenExceptionHandler,
            AccessForbiddenException,
            403,
            "Forbidden",
            logging.WARNING,
            True,
        ),
        (
            handlers.NotAcceptableExceptionHandler,
            NotAcceptableException,
            406,
            "Not Acceptable",
            logging.INFO,
            False,
        ),
        (
            handlers.PermissionDeniedExceptionHandler,
            PermissionDeniedException,
            403,
            "Permission Denied",
            logging.WARNING,
            True,
        ),
    ],
)
async def test_other_handlers(
    handler_cls: type[handlers.HandlerCallable],
    exc_cls: type[CoreException],
    status: int,
    error_type: str,
    log_level: int,
    include_path: bool,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler_instance = handler_cls()
    request = _build_request()
    caplog.set_level(log_level, logger="response_logger_test")

    if include_path:
        original = handlers.format_log_message
        monkeypatch.setattr(
            handlers,
            "format_log_message",
            lambda req, exc_obj, include_request_path=False: original(
                req, exc_obj, include_request_path=True
            ),
        )

    response = await handler_instance(request, exc_cls("failure"))

    assert response.status_code == status
    assert json.loads(response.body) == {
        "error": {"code": "failure", "message": "failure"}
    }
    assert any(
        record.levelno == log_level and "failure" in record.message
        for record in caplog.records
    )
