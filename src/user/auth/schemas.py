from pydantic import EmailStr, field_validator

from src.core.schemas import (
    Base,
    EmailNormalizationMixin,
    StrongPasswordValidationMixin,
)
from src.core.validations import (
    FULL_NAME_PATTERN,
    USERNAME_VALIDATOR,
)


class CreateUserModel(StrongPasswordValidationMixin, EmailNormalizationMixin, Base):
    first_name: str
    last_name: str
    email: EmailStr
    username: str
    password: str

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        if not FULL_NAME_PATTERN.match(value):
            raise ValueError("First name must contain latin letters and spaces only")
        return value

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, value: str) -> str:
        if not FULL_NAME_PATTERN.match(value):
            raise ValueError("Last name must contain latin letters and spaces only")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_VALIDATOR.match(value):
            raise ValueError(
                "Username must be from 4 to 60 symbols and contain alphanumeric characters, underscore, dash, and dot"
            )
        return value


class ResendVerificationModel(EmailNormalizationMixin, Base):
    email: EmailStr


class LoginUserModel(EmailNormalizationMixin, Base):
    email: EmailStr
    password: str


class SendResetPasswordRequestModel(EmailNormalizationMixin, Base):
    email: EmailStr


class ResetPasswordModel(StrongPasswordValidationMixin, Base):
    token: str
    password: str


class UserNewPassword(StrongPasswordValidationMixin, Base):
    password: str
