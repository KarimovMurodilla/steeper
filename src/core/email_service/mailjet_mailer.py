"""Mailjet email adapter implementing the AbstractMailer port."""
from pathlib import Path
from typing import Any

from mailjet_rest import Client
from pydantic import BaseModel

from loggers import get_logger
from src.core.email_service.interfaces import AbstractMailer
from src.main.config import MailjetConfig

logger = get_logger(__name__)


class MailjetMailer(AbstractMailer):
    """
    Adapter that delivers emails through the Mailjet REST API.

    Uses the Ports & Adapters pattern: this class is the *adapter* that
    translates the abstract ``AbstractMailer`` contract into concrete
    Mailjet API calls, so the rest of the application never depends on
    Mailjet directly.
    """

    def __init__(self, mailjet_config: MailjetConfig) -> None:
        self._client = Client(
            auth=(mailjet_config.MAILJET_API_KEY, mailjet_config.MAILJET_SECRET_KEY),
            version="v3.1",
        )
        self._sender_email = mailjet_config.MAILJET_SENDER_EMAIL
        self._sender_name = mailjet_config.MAILJET_SENDER_NAME

    async def send_template(
        self,
        subject: str,
        recipients: list[str],
        template_name: str,
        template_data: BaseModel | dict[str, Any],
        subtype: str = "html",
    ) -> None:
        """
        Send an email via Mailjet using an inline HTML body rendered from the
        template_data context.

        Note: Mailjet's transactional API works with HTML strings or Mailjet
        template IDs. Here we render a simple HTML body from the template_data
        dict so that the interface stays consistent with the FastAPIMailer adapter.
        """
        context: dict[str, Any] = (
            template_data
            if isinstance(template_data, dict)
            else template_data.model_dump()
        )

        html_content = self._build_html_body(subject, context)

        messages = [
            {
                "From": {"Email": self._sender_email, "Name": self._sender_name},
                "To": [{"Email": email} for email in recipients],
                "Subject": subject,
                "HTMLPart": html_content,
            }
        ]

        result = self._client.send.create(data={"Messages": messages})
        if result.status_code not in (200, 201):
            logger.error(
                "Mailjet returned unexpected status %s: %s",
                result.status_code,
                result.json(),
            )
            raise RuntimeError(
                f"Mailjet send failed with status {result.status_code}: {result.json()}"
            )

        logger.info("Mailjet email '%s' sent to %s", subject, recipients)

    async def send_with_attachments(
        self,
        subject: str,
        recipients: list[str],
        body_text: str,
        file_paths: list[Path],
        subtype: str = "plain",
    ) -> None:
        import base64

        attachments = []
        for path in file_paths:
            data = Path(path).read_bytes()
            attachments.append(
                {
                    "ContentType": "application/octet-stream",
                    "Filename": Path(path).name,
                    "Base64Content": base64.b64encode(data).decode(),
                }
            )

        messages = [
            {
                "From": {"Email": self._sender_email, "Name": self._sender_name},
                "To": [{"Email": email} for email in recipients],
                "Subject": subject,
                "TextPart": body_text,
                "Attachments": attachments,
            }
        ]

        result = self._client.send.create(data={"Messages": messages})
        if result.status_code not in (200, 201):
            logger.error(
                "Mailjet attachment send failed %s: %s",
                result.status_code,
                result.json(),
            )
            raise RuntimeError(
                f"Mailjet send failed with status {result.status_code}: {result.json()}"
            )

        logger.info(
            "Mailjet email with attachments '%s' sent to %s", subject, recipients
        )

    @staticmethod
    def _build_html_body(subject: str, context: dict[str, Any]) -> str:
        """
        Build a minimal but readable HTML email body from the context dict.
        This keeps the adapter self-contained without requiring Jinja2 at
        the Mailjet level; complex templates can use Mailjet Template IDs instead.
        """
        link = context.get("link", "")
        name = context.get("name", "")
        workspace_name = context.get("workspace_name", "")
        role = context.get("role", "")

        greeting = f"Hi {name}," if name else "Hello,"
        workspace_line = (
            f"<p>You have been invited to join the workspace <strong>{workspace_name}</strong>"
            f" as <strong>{role}</strong>.</p>"
            if workspace_name
            else ""
        )
        button = (
            f'<p><a href="{link}" style="background:#4F46E5;color:#fff;padding:12px 24px;'
            f'border-radius:6px;text-decoration:none;font-weight:bold;">Accept Invitation</a></p>'
            if link
            else ""
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Inter,sans-serif;max-width:560px;margin:auto;padding:32px;">
            <h2 style="color:#1F2937;">{subject}</h2>
            <p>{greeting}</p>
            {workspace_line}
            {button}
            <p style="color:#6B7280;font-size:13px;">
                If you did not expect this invitation, you can safely ignore this email.
            </p>
        </body>
        </html>
        """
