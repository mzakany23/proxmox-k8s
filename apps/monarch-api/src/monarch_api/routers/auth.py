"""Authentication endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..dependencies import MonarchClient
from ..schemas.auth import AuthStatus, LoginRequest, LoginResponse, MFARequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Track pending login for MFA flow
_pending_email: str | None = None
_pending_password: str | None = None


@router.get("/status", response_model=AuthStatus)
async def get_auth_status() -> AuthStatus:
    """Get current authentication status."""
    return AuthStatus(
        authenticated=MonarchClient.is_authenticated(),
        has_token=settings.has_token_auth,
        has_credentials=settings.has_credential_auth,
        email=MonarchClient.get_current_email(),
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Login with email and password."""
    global _pending_email, _pending_password
    try:
        token = await MonarchClient.login(
            email=request.email,
            password=request.password,
            use_saved_session=request.use_saved_session,
        )

        # Save token to database
        if token:
            await MonarchClient.save_token_to_db(request.email, token)

        return LoginResponse(
            authenticated=True,
            mfa_required=False,
            message="Successfully authenticated. Token saved.",
        )
    except Exception as e:
        # Check if MFA is required
        error_str = str(e).lower()
        if "mfa" in error_str or "multi-factor" in error_str or "totp" in error_str:
            _pending_email = request.email
            _pending_password = request.password
            return LoginResponse(
                authenticated=False,
                mfa_required=True,
                message="Multi-factor authentication required",
            )
        logger.exception("Login failed")
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")


@router.post("/mfa", response_model=LoginResponse)
async def submit_mfa(request: MFARequest) -> LoginResponse:
    """Submit MFA verification code."""
    global _pending_email, _pending_password

    if not _pending_email or not _pending_password:
        raise HTTPException(status_code=400, detail="No pending login. Please login first.")

    try:
        token = await MonarchClient.submit_mfa(
            email=_pending_email,
            password=_pending_password,
            code=request.code
        )

        # Save token to database
        if token and _pending_email:
            await MonarchClient.save_token_to_db(_pending_email, token)

        email = _pending_email
        _pending_email = None
        _pending_password = None

        return LoginResponse(
            authenticated=True,
            mfa_required=False,
            message="MFA verification successful. Token saved.",
        )
    except Exception as e:
        logger.exception("MFA verification failed")
        raise HTTPException(status_code=401, detail=f"MFA verification failed: {str(e)}")


@router.post("/logout")
async def logout() -> dict:
    """Logout and reset client state."""
    # Deactivate credentials in database
    if settings.has_database:
        try:
            from ..db.engine import AsyncSessionLocal
            from ..db.repositories import CredentialRepository

            async with AsyncSessionLocal() as session:
                repo = CredentialRepository(session)
                await repo.deactivate_all()
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to deactivate credentials in database: {e}")

    MonarchClient.reset()
    return {"message": "Logged out successfully"}
