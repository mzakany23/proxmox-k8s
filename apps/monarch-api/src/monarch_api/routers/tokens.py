"""API token management endpoints."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import require_scope
from ..db.engine import get_db
from ..db.models import APIToken
from ..db.repositories import APITokenRepository
from ..schemas.tokens import Token, TokenCreate, TokenList, TokenResponse

router = APIRouter(prefix="/tokens", tags=["API Tokens"])


@router.post("", response_model=TokenResponse)
async def create_token(
    request: TokenCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[APIToken, Depends(require_scope("admin"))],
) -> TokenResponse:
    """Create a new API token.

    Requires admin scope. The token value is only returned once - save it!
    """
    # Validate scope
    if request.scope not in ("read", "write", "admin"):
        raise HTTPException(status_code=400, detail="Invalid scope. Must be: read, write, or admin")

    # Generate token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now() + timedelta(days=request.expires_in_days)

    # Create token
    repo = APITokenRepository(session)
    token = await repo.create(
        token_hash=token_hash,
        name=request.name,
        scope=request.scope,
        expires_at=expires_at,
    )

    return TokenResponse(
        id=token.id,
        name=token.name,
        token=raw_token,  # Only time we return the actual token!
        scope=token.scope,
        expires_at=token.expires_at,
        created_at=token.created_at,
    )


@router.get("", response_model=TokenList)
async def list_tokens(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[APIToken, Depends(require_scope("admin"))],
    include_inactive: bool = False,
) -> TokenList:
    """List all API tokens.

    Requires admin scope. Does not include the actual token values.
    """
    repo = APITokenRepository(session)
    tokens = await repo.get_all(include_inactive=include_inactive)

    return TokenList(
        tokens=[
            Token(
                id=t.id,
                name=t.name,
                scope=t.scope,
                is_active=t.is_active,
                created_at=t.created_at,
                expires_at=t.expires_at,
                last_used_at=t.last_used_at,
            )
            for t in tokens
        ],
        total=len(tokens),
    )


@router.get("/{token_id}", response_model=Token)
async def get_token(
    token_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[APIToken, Depends(require_scope("admin"))],
) -> Token:
    """Get details about a specific API token.

    Requires admin scope. Does not include the actual token value.
    """
    repo = APITokenRepository(session)
    token = await repo.get_by_id(token_id)

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    return Token(
        id=token.id,
        name=token.name,
        scope=token.scope,
        is_active=token.is_active,
        created_at=token.created_at,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
    )


@router.delete("/{token_id}")
async def revoke_token(
    token_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[APIToken, Depends(require_scope("admin"))],
) -> dict:
    """Revoke (deactivate) an API token.

    Requires admin scope. The token will no longer work after revocation.
    """
    repo = APITokenRepository(session)
    token = await repo.get_by_id(token_id)

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    success = await repo.revoke(token_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to revoke token")

    return {"message": "Token revoked", "id": token_id}
