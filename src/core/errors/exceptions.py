from typing import Any

from src.core.errors.enums import ErrorCode


class CoreException(Exception):
    def __init__(
        self,
        code: ErrorCode | None = None,
        params: dict[str, Any] | None = None,
        additional_info: dict[str, Any] | None = None,
    ):
        self.code = code or ErrorCode.INTERNAL_SERVER_ERROR
        self.params = params or {}
        self.additional_info = additional_info


class InfrastructureException(CoreException):
    pass


class InstanceNotFoundException(CoreException):
    pass


class InstanceAlreadyExistsException(CoreException):
    pass


class InstanceProcessingException(CoreException):
    pass


class PayloadTooLargeException(CoreException):
    pass


class FilteringError(CoreException):
    pass


class UnauthorizedException(CoreException):
    pass


class AccessForbiddenException(CoreException):
    pass


class NotAcceptableException(CoreException):
    pass


class PermissionDeniedException(CoreException):
    pass


class TooManyRequestsException(CoreException):
    def __init__(
        self,
        code: ErrorCode | None = None,
        retry_after: int | None = None,
        additional_info: dict[str, Any] | None = None,
    ):
        super().__init__(code, additional_info)
        self.retry_after = retry_after
