"""Mock email provider for testing."""

from typing import Optional
import logging
from app.domain.interfaces import IEmailProvider

logger = logging.getLogger(__name__)


class MockEmailProvider(IEmailProvider):
    """Mock email provider that logs instead of sending."""
    
    def __init__(self):
        self.sent_emails = []
    
    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Log email instead of sending."""
        email = {
            "to": to,
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
        }
        self.sent_emails.append(email)
        logger.info(f"Mock email sent to {to}: {subject}")
        return True
    
    async def send_otp(
        self,
        to: str,
        code: str,
        action: str = "verify",
    ) -> bool:
        """Send OTP email (mocked)."""
        subject = f"Your {action.title()} Code"
        html_content = f"<p>Your {action} code is: <strong>{code}</strong></p>"
        return await self.send(to, subject, html_content)
