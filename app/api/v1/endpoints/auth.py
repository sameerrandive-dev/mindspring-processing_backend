"""
Refactored authentication endpoints.

Endpoints are thin HTTP handlers that:
- Validate requests using Pydantic schemas
- Get services from the DI container
- Call services for business logic
- Convert DomainErrors to HTTP responses
- Return DTOs (not domain models)
"""

import logging
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from fastapi.responses import RedirectResponse

from app.api.deps import get_current_user, get_service_container
from app.domain.models.user import User
from app.domain.schemas.auth import (
    UserCreate, UserLogin, Token, UserResponse, OTPVerify, Msg,
    PasswordResetRequest, PasswordReset, ResendOTPRequest
)
from app.domain.errors import DomainError, AuthError, ValidationError
from app.infrastructure.container import ServiceContainer
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)



# ============================================================================
# DEPENDENCY PROVIDERS
# ============================================================================

async def get_auth_service(container: ServiceContainer = Depends(get_service_container)):
    """Get AuthService from container."""
    return container.get_auth_service()


# ============================================================================
# ENDPOINTS - THIN HTTP HANDLERS
# ============================================================================

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserCreate,
    service=Depends(get_auth_service),
):
    """Create new user and send OTP."""
    logger.info(f"Signup request for email: {user_in.email}")
    user, otp_code = await service.register_user(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
    )
    logger.info(f"Signup successful for: {user_in.email}")
    return UserResponse.model_validate(user)


@router.post("/verify-otp", response_model=Msg)
async def verify_otp(
    data: OTPVerify,
    service=Depends(get_auth_service),
):
    """Verify OTP and activate account."""
    await service.verify_email(email=data.email, otp_code=data.code)
    return {"message": "Email verified successfully"}


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    user_in: UserLogin,
    service=Depends(get_auth_service),
):
    """Login and set refresh token in HTTP-only cookie."""
    access_token, refresh_token, user = await service.login(
        email=user_in.email,
        password=user_in.password,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,
        samesite="lax",
        secure=True,
    )
    logger.info(f"Login successful: {user_in.email}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    service=Depends(get_auth_service),
):
    """Refresh access token using refresh token from cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise AuthError("Refresh token not provided")
    
    new_access_token, new_refresh_token = await service.refresh_tokens(refresh_token)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,
        samesite="lax",
        secure=True,
    )
    logger.info("Token refresh successful")
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


@router.post("/logout", response_model=Msg)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    service=Depends(get_auth_service),
):
    """Logout by revoking refresh token."""
    refresh_token = request.cookies.get("refresh_token")
    await service.logout(user_id=current_user.id, refresh_token=refresh_token)
    response.delete_cookie("refresh_token")
    logger.info(f"Logout successful: {current_user.id}")
    return {"message": "Logged out successfully"}


@router.post("/resend-otp", response_model=Msg)
async def resend_otp(
    data: ResendOTPRequest,
    service=Depends(get_auth_service),
):
    """Resend OTP to user email."""
    await service.resend_otp(email=data.email)
    return {"message": "OTP resent successfully"}


@router.post("/forgot-password", response_model=Msg)
async def forgot_password(
    data: PasswordResetRequest,
    service=Depends(get_auth_service),
):
    """Request password reset by sending OTP to email."""
    await service.request_password_reset(email=data.email)
    # Always return success message for security (don't reveal if email exists)
    return {"message": "If the email exists, a password reset code has been sent"}


@router.post("/reset-password", response_model=Msg)
async def reset_password(
    data: PasswordReset,
    service=Depends(get_auth_service),
):
    """Reset password using OTP verification."""
    await service.reset_password(
        email=data.email,
        otp_code=data.code,
        new_password=data.new_password,
    )
    return {"message": "Password reset successfully"}


@router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth login."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )
    
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{google_auth_url}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    response: Response,
    code: str = Query(...),
    service=Depends(get_auth_service),
):
    """Handle Google OAuth callback."""
    from app.core.oauth import google_oauth
    
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured"
        )
    
    # Exchange code for tokens
    tokens = await google_oauth.get_tokens(code)
    access_token_google = tokens["access_token"]
    
    # Get user info from Google
    user_info = await google_oauth.get_user_info(access_token_google)
    email = user_info.get("email")
    google_id = user_info.get("sub")
    name = user_info.get("name")
    
    if not email or not google_id:
        raise HTTPException(
            status_code=400,
            detail="Failed to retrieve user information from Google"
        )
    
    # Login or register user via Google
    access_token, refresh_token, user = await service.google_login(
        google_id=google_id,
        email=email,
        name=name,
    )
    
    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,
        samesite="lax",
        secure=True,
    )
    
    logger.info(f"Google OAuth successful: {email}")
    
    # Return JSON response with token (for API clients)
    # In production, you might want to redirect to a frontend URL instead
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
        "user": UserResponse.model_validate(user).model_dump(),
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    return UserResponse.model_validate(current_user)
