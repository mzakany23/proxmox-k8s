"""FastAPI dependencies for API token authentication."""

import hashlib
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.engine import get_db
from ..db.models import APIToken
from ..db.repositories import APITokenRepository

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> APIToken | None:
    """Get the current API token if provided and valid.

    Returns None if no token provided (for optional auth).
    Raises HTTPException if token provided but invalid.
    """
    if credentials is None:
        return None

    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    repo = APITokenRepository(session)
    token = await repo.get_by_hash(token_hash)

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last used timestamp (fire and forget)
    await repo.update_last_used(token.id)

    return token


async def require_api_token(
    token: Annotated[APIToken | None, Depends(get_current_token)],
) -> APIToken:
    """Require a valid API token.

    Use this as a dependency when authentication is required.
    """
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="API token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def require_scope(required_scope: str):
    """Create a dependency that requires a specific scope.

    Scope hierarchy: admin > write > read

    Args:
        required_scope: The minimum scope required ("read", "write", or "admin")

    Returns:
        A FastAPI dependency function
    """
    scope_hierarchy = {"read": 0, "write": 1, "admin": 2}

    async def check_scope(
        token: Annotated[APIToken, Depends(require_api_token)],
    ) -> APIToken:
        token_level = scope_hierarchy.get(token.scope, 0)
        required_level = scope_hierarchy.get(required_scope, 0)

        if token_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required scope: {required_scope}, your scope: {token.scope}",
            )
        return token

    return check_scope
