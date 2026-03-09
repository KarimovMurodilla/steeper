from pydantic import Field

from src.core.schemas import Base


class MailTemplateDataBody(Base):
    title: str = Field(..., description="Email title", examples=["Welcome!"])
    link: str = Field(..., description="Action link", examples=["https://example.com"])


class MailTemplateBodyFile(Base):
    title: str = Field(..., description="Email title", examples=["Your Report"])
    file: str = Field(
        ..., description="Attachment file path or URL", examples=["/tmp/report.pdf"]
    )


class MailTemplateVerificationBody(Base):
    title: str = Field(..., description="Email title", examples=["Verify your email"])
    link: str = Field(
        ..., description="Verification link", examples=["https://example.com/verify"]
    )
    name: str = Field(..., description="User's name", examples=["John Doe"])


class MailTemplateNotificationBody(MailTemplateVerificationBody):
    pass


class MailTemplateResetPasswordBody(MailTemplateVerificationBody):
    pass
