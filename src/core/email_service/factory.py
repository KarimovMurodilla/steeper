from src.core.email_service.config import get_fastapi_mail_config
from src.core.email_service.fastapi_mailer import FastAPIMailer
from src.core.email_service.interfaces import AbstractMailer
from src.core.email_service.mailjet_mailer import MailjetMailer
from src.main.config import config


class MailerFactory:
    """
    Factory that instantiates the correct AbstractMailer adapter based on the
    configured backend.  Adding a new provider requires only:
      1. Creating a new AbstractMailer subclass
      2. Adding a branch here
    The rest of the codebase remains untouched.
    """

    @staticmethod
    def create(backend: str) -> AbstractMailer:
        """
        Args:
            backend: One of ``"mailjet"`` | ``"smtp"``

        Returns:
            A concrete AbstractMailer implementation.

        Raises:
            ValueError: If the backend name is not recognised.
        """
        backend = backend.lower().strip()

        if backend == "mailjet":
            return MailjetMailer(config.mailjet)

        if backend == "smtp":
            return FastAPIMailer(get_fastapi_mail_config())

        raise ValueError(
            f"Unknown MAILER_BACKEND '{backend}'. Valid options: 'mailjet', 'smtp'."
        )
