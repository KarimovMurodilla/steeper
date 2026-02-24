from src.core.email_service.factory import MailerFactory
from src.core.email_service.service import EmailService
from src.main.config import config


def get_email_service() -> EmailService:
    """
    FastAPI dependency that returns a fully configured EmailService.

    The concrete mailer adapter (Mailjet, SMTP, …) is selected by the
    ``MAILER_BACKEND`` environment variable via ``MailerFactory``.
    """
    mailer = MailerFactory.create(config.app.MAILER_BACKEND)
    return EmailService(mailer)
