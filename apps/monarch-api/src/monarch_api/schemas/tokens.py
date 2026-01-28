"""API token request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TokenCreate(BaseModel):
    """Request body for creating an API token."""

    name: str = Field(description="Human-readable name for the token")
    scope: str = Field(default="read", description="Token scope: read, write, or admin")
    expires_in_days: int | None = Field(
        default=None,
        description="Number of days until token expires. None for no expiration.",
        ge=1,
        le=365,
    )


class TokenResponse(BaseModel):
    """Response containing the created token (only returned once!)."""

    id: int = Field(description="Token ID")
    name: str = Field(description="Token name")
    token: str = Field(description="The API token (save this - it won't be shown again!)")
    scope: str = Field(description="Token scope")
    expires_at: datetime | None = Field(description="When the token expires, if ever")
    created_at: datetime = Field(description="When the token was created")


class Token(BaseModel):
    """API token info (without the actual token value)."""

    id: int = Field(description="Token ID")
    name: str = Field(description="Token name")
    scope: str = Field(description="Token scope")
    is_active: bool = Field(description="Whether the token is active")
    created_at: datetime = Field(description="When the token was created")
    expires_at: datetime | None = Field(description="When the token expires, if ever")
    last_used_at: datetime | None = Field(description="When the token was last used")


class TokenList(BaseModel):
    """List of API tokens."""

    tokens: list[Token] = Field(description="List of API tokens")
    total: int = Field(description="Total number of tokens")
