"""User repository for authentication and profile management."""

from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.user import User
from app.domain.models.refresh_token import RefreshToken
from app.domain.models.otp import OTP
from app.domain.errors import NotFoundError


class UserRepository:
    """Repository for User entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        google_id: Optional[str] = None,
        is_verified: bool = False,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            google_id=google_id,
            is_verified=is_verified,
        )
        self.db.add(user)
        await self.db.flush()
        return user
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        result = await self.db.execute(select(User).where(User.google_id == google_id))
        return result.scalar_one_or_none()
    
    async def update(self, user_id: str, **updates) -> User:
        """Update user fields."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found", resource_type="User", resource_id=user_id)
        
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        await self.db.flush()
        return user
    
    async def delete(self, user_id: str) -> bool:
        """Delete user by ID."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        await self.db.delete(user)
        await self.db.flush()
        return True
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users."""
        result = await self.db.execute(
            select(User).offset(skip).limit(limit).order_by(desc(User.created_at))
        )
        return result.scalars().all()
    
    # ========================================================================
    # Refresh Token Operations
    # ========================================================================
    
    async def create_refresh_token(
        self,
        user_id: str,
        token: str,
        expires_at,
    ) -> RefreshToken:
        """Create a refresh token."""
        rt = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )
        self.db.add(rt)
        await self.db.flush()
        return rt
    
    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by value."""
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()
    
    async def revoke_refresh_token(self, token: str) -> bool:
        """Revoke (invalidate) a refresh token."""
        rt = await self.get_refresh_token(token)
        if not rt:
            return False
        
        rt.is_revoked = True
        await self.db.flush()
        return True
    
    async def revoke_all_user_tokens(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user."""
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.is_revoked = True
        await self.db.flush()
    
    # ========================================================================
    # OTP Operations
    # ========================================================================
    
    async def create_otp(
        self,
        email: str,
        code: str,
        otp_type: str,
        expires_at,
    ) -> OTP:
        """Create an OTP record."""
        otp = OTP(
            email=email,
            code=code,
            type=otp_type,
            expires_at=expires_at,
        )
        self.db.add(otp)
        await self.db.flush()
        return otp
    
    async def get_otp_by_code(self, email: str, code: str) -> Optional[OTP]:
        """Get OTP by email and code."""
        result = await self.db.execute(
            select(OTP).where(OTP.email == email, OTP.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_otp_by_code_and_type(self, email: str, code: str, otp_type: str) -> Optional[OTP]:
        """Get OTP by email, code, and type."""
        result = await self.db.execute(
            select(OTP).where(
                OTP.email == email,
                OTP.code == code,
                OTP.type == otp_type
            )
        )
        return result.scalar_one_or_none()
    
    async def delete_otp(self, otp_id: int) -> bool:
        """Delete OTP by ID."""
        otp = await self.db.get(OTP, otp_id)
        if not otp:
            return False
        
        await self.db.delete(otp)
        await self.db.flush()
        return True
    
    async def delete_otp_by_email(self, email: str) -> None:
        """Delete all OTPs for an email."""
        result = await self.db.execute(select(OTP).where(OTP.email == email))
        otps = result.scalars().all()
        for otp in otps:
            await self.db.delete(otp)
        await self.db.flush()
    
    async def delete_otp_by_email_and_type(self, email: str, otp_type: str) -> None:
        """Delete all OTPs for an email with a specific type."""
        result = await self.db.execute(
            select(OTP).where(OTP.email == email, OTP.type == otp_type)
        )
        otps = result.scalars().all()
        for otp in otps:
            await self.db.delete(otp)
        await self.db.flush()


class RefreshTokenRepository:
    """Repository for RefreshToken entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by value."""
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()
    
    async def revoke(self, token: str) -> bool:
        """Mark token as revoked."""
        rt = await self.get_by_token(token)
        if not rt:
            return False
        
        rt.is_revoked = True
        await self.db.flush()
        return True
