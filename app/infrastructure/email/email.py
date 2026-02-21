"""Email service for sending OTP and other notifications."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_otp_email(email: str, otp_code: str, otp_type: str = "signup") -> bool:
    """
    Send OTP email to user.
    
    Args:
        email: Recipient email address
        otp_code: OTP code to send
        otp_type: Type of OTP (signup, login, password_reset, etc.)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check if SMTP is configured
    if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
        logger.error("SMTP configuration is incomplete. Cannot send email.")
        return False
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Your MindSpring Verification Code"
        message["From"] = settings.EMAIL_FROM or settings.SMTP_USERNAME
        message["To"] = email
        
        # Create HTML content
        html_content = _create_otp_email_html(otp_code, otp_type)
        
        # Create plain text fallback
        text_content = f"""
        Your MindSpring Verification Code
        
        Your verification code is: {otp_code}
        
        This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.
        
        If you didn't request this code, please ignore this email.
        
        Best regards,
        The MindSpring Team
        """
        
        # Attach parts
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
        
        logger.info(f"OTP email sent successfully to {email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred while sending email to {email}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email to {email}: {str(e)}")
        return False


def _create_otp_email_html(otp_code: str, otp_type: str) -> str:
    """
    Create HTML content for OTP email.
    
    Args:
        otp_code: OTP code to include
        otp_type: Type of OTP
    
    Returns:
        str: HTML content
    """
    action_text = {
        "signup": "verify your account",
        "login": "log in to your account",
        "password_reset": "reset your password"
    }.get(otp_type, "verify your request")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Verification Code</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 40px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 40px 40px 20px 40px; text-align: center;">
                                <h1 style="margin: 0; color: #333333; font-size: 28px; font-weight: 600;">MindSpring</h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 20px 40px;">
                                <h2 style="margin: 0 0 20px 0; color: #333333; font-size: 20px; font-weight: 600;">Your Verification Code</h2>
                                <p style="margin: 0 0 20px 0; color: #666666; font-size: 16px; line-height: 1.5;">
                                    Use the following code to {action_text}:
                                </p>
                                
                                <!-- OTP Code Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                    <tr>
                                        <td align="center" style="background-color: #f8f9fa; border-radius: 8px; padding: 30px;">
                                            <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #333333; font-family: 'Courier New', monospace;">
                                                {otp_code}
                                            </span>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 20px 0 0 0; color: #666666; font-size: 14px; line-height: 1.5;">
                                    This code will expire in <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>.
                                </p>
                                <p style="margin: 20px 0 0 0; color: #999999; font-size: 14px; line-height: 1.5;">
                                    If you didn't request this code, please ignore this email.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px 40px; border-top: 1px solid #eeeeee; text-align: center;">
                                <p style="margin: 0; color: #999999; font-size: 12px;">
                                    © 2026 MindSpring. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
