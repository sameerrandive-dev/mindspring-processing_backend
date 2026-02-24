"""SMTP email provider implementation."""

import asyncio
from typing import Optional
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.domain.interfaces import IEmailProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class SMTPEmailProvider(IEmailProvider):
    """SMTP email provider for sending real emails."""
    
    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send email via SMTP."""
        # Check if SMTP is configured
        if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            logger.error("SMTP configuration is incomplete. Cannot send email.")
            return False
        
        # Use a function for the blocking SMTP logic
        def _send_sync():
            try:
                # Create message
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = settings.EMAIL_FROM or settings.SMTP_USERNAME
                message["To"] = to
                
                # Attach text content if provided
                if text_content:
                    part1 = MIMEText(text_content, "plain")
                    message.attach(part1)
                
                # Attach HTML content
                part2 = MIMEText(html_content, "html")
                message.attach(part2)
                
                # Determine protocol based on port
                port = int(settings.SMTP_PORT)
                host = settings.SMTP_HOST
                
                if port == 465:
                    # Use SSL for port 465
                    server_class = smtplib.SMTP_SSL
                else:
                    # Use standard SMTP for others (STARTTLS will be used for 587)
                    server_class = smtplib.SMTP

                with server_class(host, port, timeout=10) as server:
                    # Use STARTTLS for port 587 or if explicitly requested
                    if port == 587:
                        server.starttls()
                    
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(message)
                return True
            except Exception as e:
                logger.error(f"Sync SMTP send failed: {str(e)}")
                raise e

        try:
            # Run blocking SMTP in a separate thread to avoid blocking event loop
            return await asyncio.to_thread(_send_sync)
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            return False
        except (smtplib.SMTPException, ConnectionError, TimeoutError) as e:
            logger.error(f"SMTP error occurred while sending email to {to}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to}: {str(e)}", exc_info=True)
            return False
    
    async def send_otp(
        self,
        to: str,
        code: str,
        action: str = "verify",
    ) -> bool:
        """Send OTP email via SMTP."""
        from app.infrastructure.email.email import _create_otp_email_html
        
        subject = f"Your MindSpring Verification Code"
        html_content = _create_otp_email_html(code, action)
        text_content = f"""Your MindSpring Verification Code

Your verification code is: {code}

This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

If you didn't request this code, please ignore this email.

Best regards,
The MindSpring Team
"""
        result = await self.send(to, subject, html_content, text_content)
        if not result:
            logger.warning(f"--- FAILED TO SEND EMAIL ---")
            logger.warning(f"TO: {to}")
            logger.warning(f"ACTION: {action}")
            logger.warning(f"CODE: {code}")
            logger.warning(f"---------------------------")
        return result
