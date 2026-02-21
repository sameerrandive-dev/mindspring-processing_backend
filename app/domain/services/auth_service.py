"""Authentication service for user management and token operations."""

import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
import secrets

from app.domain.models.user import User
from app.domain.models.refresh_token import RefreshToken
from app.domain.repositories.user_repository import UserRepository
from app.domain.errors import (
    ValidationError,
    NotFoundError,
    AuthError,
    ConflictError,
    ErrorCode,
)
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token as create_rt_token,
)
from app.domain.interfaces import IEmailProvider

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service handling user registration, login, and token management.
    
    Pure business logic - no FastAPI or HTTP knowledge.
    Delegates to:
    - UserRepository for data access
    - IEmailProvider for OTP delivery
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        email_provider: IEmailProvider,
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        self.user_repo = user_repo
        self.email_provider = email_provider
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
    
    async def register_user(
        self,
        email: str,
        password: str,
    ) -> Tuple[User, str]:
        """
        Register a new user with email and password.
        
        Returns:
            Tuple of (User, OTP code) - caller sends OTP to user via email
            
        Raises:
            ValidationError: invalid email/password
            ConflictError: email already registered
        """
        # Validate email format
        if not email or "@" not in email:
            raise ValidationError("Invalid email format")
        
        # Validate password strength
        if not password or len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        # Check if email already exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError(
                f"Email {email} is already registered",
                code=ErrorCode.ALREADY_EXISTS,
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(password)
        user = await self.user_repo.create(
            email=email,
            hashed_password=hashed_password,
            is_verified=False,
        )
        
        # Generate OTP
        otp_code = self._generate_otp()
        
        # Store OTP in database
        otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        await self.user_repo.create_otp(
            email=email,
            code=otp_code,
            otp_type="signup",
            expires_at=otp_expires,
        )
        
        # Send OTP email
        await self.email_provider.send_otp(to=email, code=otp_code, action="verify")
        
        logger.info(f"User registered: {email}")
        return user, otp_code
    
    async def verify_email(self, email: str, otp_code: str) -> User:
        """
        Verify user email with OTP.
        
        Raises:
            NotFoundError: user or OTP not found
            ValidationError: OTP invalid or expired
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundError(f"User with email {email} not found", resource_type="User")
        
        # Get OTP record (only signup OTPs for email verification)
        otp = await self.user_repo.get_otp_by_code_and_type(email, otp_code, "signup")
        if not otp:
            raise ValidationError("Invalid OTP code")
        
        # Check expiration
        if datetime.now(timezone.utc) > otp.expires_at:
            raise ValidationError("OTP has expired")
        
        # Mark user as verified
        user = await self.user_repo.update(user.id, is_verified=True)
        
        # Delete used OTP
        await self.user_repo.delete_otp(otp.id)
        
        logger.info(f"Email verified: {email}")
        return user
    
    async def login(self, email: str, password: str) -> Tuple[str, str, User]:
        """
        Authenticate user and issue tokens.
        
        Returns:
            Tuple of (access_token, refresh_token, user)
            
        Raises:
            AuthError: invalid credentials or unverified email
        """
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password", code=ErrorCode.INVALID_CREDENTIALS)
        
        if not user.is_verified:
            raise AuthError(
                "Email not verified. Please verify your email first.",
                code=ErrorCode.FORBIDDEN,
            )
        
        if not user.is_active:
            raise AuthError("Account is inactive", code=ErrorCode.FORBIDDEN)
        
        # Create tokens
        access_token = create_access_token(
            {"sub": str(user.id)},
            expires_delta=timedelta(minutes=self.access_token_expire_minutes),
        )
        
        refresh_token = create_rt_token(
            {"sub": str(user.id)},
            expires_delta=timedelta(days=self.refresh_token_expire_days),
        )
        
        # Store refresh token in database
        rt_expires = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        await self.user_repo.create_refresh_token(
            user_id=user.id,
            token=refresh_token,
            expires_at=rt_expires,
        )
        
        logger.info(f"User logged in: {email}")
        return access_token, refresh_token, user
    
    async def refresh_tokens(self, refresh_token: str) -> Tuple[str, str]:
        """
        Issue new tokens using a valid refresh token.
        
        Returns:
            Tuple of (new_access_token, new_refresh_token)
            
        Raises:
            AuthError: invalid, expired, or revoked refresh token
        """
        rt = await self.user_repo.get_refresh_token(refresh_token)
        if not rt:
            raise AuthError("Invalid refresh token", code=ErrorCode.TOKEN_INVALID)
        
        if rt.is_revoked:
            raise AuthError("Refresh token has been revoked", code=ErrorCode.TOKEN_INVALID)
        
        if datetime.now(timezone.utc) > rt.expires_at:
            raise AuthError("Refresh token has expired", code=ErrorCode.TOKEN_EXPIRED)
        
        # Get user
        user = await self.user_repo.get_by_id(rt.user_id)
        if not user or not user.is_active:
            raise AuthError("User not found or inactive", code=ErrorCode.FORBIDDEN)
        
        # Revoke old token
        await self.user_repo.revoke_refresh_token(refresh_token)
        
        # Create new tokens
        new_access_token = create_access_token(
            {"sub": str(user.id)},
            expires_delta=timedelta(minutes=self.access_token_expire_minutes),
        )
        
        new_refresh_token = create_rt_token(
            {"sub": str(user.id)},
            expires_delta=timedelta(days=self.refresh_token_expire_days),
        )
        
        # Store new refresh token
        rt_expires = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        await self.user_repo.create_refresh_token(
            user_id=user.id,
            token=new_refresh_token,
            expires_at=rt_expires,
        )
        
        logger.info(f"Tokens refreshed for user: {user.id}")
        return new_access_token, new_refresh_token
    
    async def logout(self, user_id: str, refresh_token: Optional[str] = None) -> None:
        """
        Logout user by revoking refresh tokens.
        
        If refresh_token is provided, only that token is revoked.
        Otherwise, all tokens for the user are revoked.
        """
        if refresh_token:
            await self.user_repo.revoke_refresh_token(refresh_token)
            logger.info(f"Single token revoked for user: {user_id}")
        else:
            await self.user_repo.revoke_all_user_tokens(user_id)
            logger.info(f"All tokens revoked for user: {user_id}")
    
    async def resend_otp(self, email: str) -> str:
        """
        Resend OTP to user email.
        
        Returns:
            OTP code (for testing purposes)
            
        Raises:
            NotFoundError: user not found
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundError(f"User with email {email} not found", resource_type="User")
        
        # Generate new OTP
        otp_code = self._generate_otp()
        
        # Delete old OTPs
        await self.user_repo.delete_otp_by_email(email)
        
        # Create new OTP
        otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        await self.user_repo.create_otp(
            email=email,
            code=otp_code,
            otp_type="signup",
            expires_at=otp_expires,
        )
        
        # Send email
        await self.email_provider.send_otp(to=email, code=otp_code, action="verify")
        
        logger.info(f"OTP resent to: {email}")
        return otp_code
    
    async def request_password_reset(self, email: str) -> str:
        """
        Request password reset by sending OTP to user email.
        
        Returns:
            OTP code (for testing purposes)
            
        Raises:
            NotFoundError: user not found
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal if user exists or not for security
            # Still return success message but don't send email
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return ""
        
        # Generate new OTP
        otp_code = self._generate_otp()
        
        # Delete old password reset OTPs for this email
        await self.user_repo.delete_otp_by_email_and_type(email, "password_reset")
        
        # Create new password reset OTP
        otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        await self.user_repo.create_otp(
            email=email,
            code=otp_code,
            otp_type="password_reset",
            expires_at=otp_expires,
        )
        
        # Send password reset email
        await self.email_provider.send_otp(to=email, code=otp_code, action="password_reset")
        
        logger.info(f"Password reset OTP sent to: {email}")
        return otp_code
    
    async def reset_password(self, email: str, otp_code: str, new_password: str) -> User:
        """
        Reset user password using OTP verification.
        
        Returns:
            Updated User object
            
        Raises:
            NotFoundError: user not found
            ValidationError: invalid OTP, expired OTP, or weak password
        """
        # Validate password strength
        if not new_password or len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundError(f"User with email {email} not found", resource_type="User")
        
        # Get password reset OTP record
        otp = await self.user_repo.get_otp_by_code_and_type(email, otp_code, "password_reset")
        if not otp:
            raise ValidationError("Invalid OTP code")
        
        # Check expiration
        if datetime.now(timezone.utc) > otp.expires_at:
            raise ValidationError("OTP has expired")
        
        # Hash new password and update user
        hashed_password = get_password_hash(new_password)
        user = await self.user_repo.update(user.id, hashed_password=hashed_password)
        
        # Delete used OTP
        await self.user_repo.delete_otp(otp.id)
        
        # Revoke all refresh tokens for security
        await self.user_repo.revoke_all_user_tokens(user.id)
        
        logger.info(f"Password reset successful for: {email}")
        return user
    
    async def google_login(self, google_id: str, email: str, name: Optional[str] = None) -> Tuple[str, str, User]:
        """
        Login or register user via Google OAuth.
        
        If user exists with Google ID, log them in.
        If user exists with email but no Google ID, link Google account.
        If user doesn't exist, create new account (auto-verified).
        
        Returns:
            Tuple of (access_token, refresh_token, user)
        """
        # Check if user exists with this Google ID
        user = await self.user_repo.get_by_google_id(google_id)
        
        if user:
            # User exists with Google ID - log them in
            if not user.is_active:
                raise AuthError("Account is inactive", code=ErrorCode.FORBIDDEN)
            
            # Update email if changed
            if email and user.email != email:
                user = await self.user_repo.update(user.id, email=email)
        else:
            # Check if user exists with this email
            user = await self.user_repo.get_by_email(email)
            
            if user:
                # User exists with email but no Google ID - link Google account
                user = await self.user_repo.update(user.id, google_id=google_id, is_verified=True)
            else:
                # New user - create account (auto-verified for Google users)
                # Generate a random password (user won't need it, but required by schema)
                random_password = secrets.token_urlsafe(32)
                hashed_password = get_password_hash(random_password)
                
                user = await self.user_repo.create(
                    email=email,
                    hashed_password=hashed_password,
                    google_id=google_id,
                    is_verified=True,  # Google emails are pre-verified
                )
        
        # Create tokens
        access_token = create_access_token(
            {"sub": str(user.id)},
            expires_delta=timedelta(minutes=self.access_token_expire_minutes),
        )
        
        refresh_token = create_rt_token(
            {"sub": str(user.id)},
            expires_delta=timedelta(days=self.refresh_token_expire_days),
        )
        
        # Store refresh token in database
        rt_expires = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        await self.user_repo.create_refresh_token(
            user_id=user.id,
            token=refresh_token,
            expires_at=rt_expires,
        )
        
        logger.info(f"Google login successful: {email} (Google ID: {google_id})")
        return access_token, refresh_token, user
    
    def _generate_otp(self) -> str:
        """Generate a random 6-digit OTP."""
        return "".join([str(secrets.randbelow(10)) for _ in range(6)])
