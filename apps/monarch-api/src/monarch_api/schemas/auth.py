"""Authentication request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request body for login endpoint."""

    email: EmailStr = Field(description="Monarch Money account email")
    password: str = Field(description="Monarch Money account password")
    use_saved_session: bool = Field(default=True, description="Whether to save session for future use")


class MFARequest(BaseModel):
    """Request body for MFA verification."""

    code: str = Field(description="Multi-factor authentication code")


class LoginResponse(BaseModel):
    """Response from successful login."""

    authenticated: bool = Field(description="Whether authentication was successful")
    mfa_required: bool = Field(default=False, description="Whether MFA is needed")
    message: str = Field(description="Status message")


class AuthStatus(BaseModel):
    """Current authentication status."""

    authenticated: bool = Field(description="Whether client is authenticated")
    has_token: bool = Field(description="Whether a token is configured")
    has_credentials: bool = Field(description="Whether email/password are configured")
    email: str | None = Field(default=None, description="Email of authenticated user")
