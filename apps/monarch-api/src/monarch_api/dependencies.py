"""MonarchMoney client singleton with lazy authentication."""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import HTTPException
from monarchmoney import MonarchMoney
from monarchmoney.monarchmoney import MonarchMoneyEndpoints

from .config import settings

logger = logging.getLogger(__name__)

# Patch MonarchMoneyEndpoints to use the new API domain (changed from monarchmoney.com to monarch.com)
MonarchMoneyEndpoints.BASE_URL = "https://api.monarch.com"


class MonarchClient:
    """Singleton wrapper for MonarchMoney client with lazy initialization."""

    _instance: MonarchMoney | None = None
    _authenticated: bool = False
    _lock: asyncio.Lock | None = None
    _current_email: str | None = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """Get or create the async lock."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    async def _get_db_token(cls) -> tuple[str, str] | None:
        """Try to get token from database. Returns (email, token) or None."""
        if not settings.has_database:
            return None

        try:
            from .db.engine import AsyncSessionLocal
            from .db.repositories import CredentialRepository

            async with AsyncSessionLocal() as session:
                repo = CredentialRepository(session)
                credential = await repo.get_active()
                if credential:
                    logger.info(f"Found active credential in database for {credential.email}")
                    return (credential.email, credential.token)
        except Exception as e:
            logger.warning(f"Failed to get token from database: {e}")

        return None

    @classmethod
    async def save_token_to_db(cls, email: str, token: str) -> bool:
        """Save token to database. Returns True on success."""
        if not settings.has_database:
            logger.warning("Database not configured, cannot save token")
            return False

        try:
            from .db.engine import AsyncSessionLocal
            from .db.repositories import CredentialRepository

            async with AsyncSessionLocal() as session:
                repo = CredentialRepository(session)
                await repo.save(email, token)
                await session.commit()
                logger.info(f"Saved token to database for {email}")
                return True
        except Exception as e:
            logger.error(f"Failed to save token to database: {e}")
            return False

    @classmethod
    async def get_client(cls) -> MonarchMoney:
        """Get the MonarchMoney client, initializing if needed."""
        async with cls._get_lock():
            if cls._instance is None:
                # Try database first, then fall back to env vars
                db_creds = await cls._get_db_token()
                if db_creds:
                    email, token = db_creds
                    cls._instance = MonarchMoney(token=token)
                    cls._current_email = email
                    cls._authenticated = True
                elif settings.has_token_auth:
                    cls._instance = MonarchMoney(token=settings.monarch_token)
                    cls._authenticated = True
                else:
                    cls._instance = MonarchMoney()

            if not cls._authenticated:
                await cls._authenticate()

            return cls._instance

    @classmethod
    async def _authenticate(cls) -> None:
        """Authenticate the client using configured credentials."""
        if cls._instance is None:
            raise RuntimeError("Client not initialized")

        if settings.has_token_auth:
            # Token already set in constructor
            cls._authenticated = True
        elif settings.has_credential_auth:
            # Login with email/password
            await cls._instance.login(
                email=settings.monarch_email,
                password=settings.monarch_password,
                use_saved_session=True,
            )
            cls._authenticated = True
        else:
            raise HTTPException(
                status_code=401,
                detail="No authentication configured. Please login at /auth",
            )

    @classmethod
    def is_authenticated(cls) -> bool:
        """Check if client is authenticated."""
        return cls._authenticated

    @classmethod
    def get_current_email(cls) -> str | None:
        """Get the email of the currently authenticated user."""
        return cls._current_email

    @classmethod
    async def login(cls, email: str, password: str, use_saved_session: bool = True) -> str | None:
        """Manually login with credentials. Returns token on success."""
        async with cls._get_lock():
            if cls._instance is None:
                cls._instance = MonarchMoney()

            await cls._instance.login(
                email=email,
                password=password,
                use_saved_session=use_saved_session,
            )
            cls._authenticated = True
            cls._current_email = email

            # Return the token for saving
            return cls._instance.token

    @classmethod
    async def submit_mfa(cls, email: str, password: str, code: str) -> str | None:
        """Submit MFA code. Returns token on success."""
        if cls._instance is None:
            cls._instance = MonarchMoney()

        await cls._instance.multi_factor_authenticate(email, password, code)
        cls._authenticated = True
        cls._current_email = email

        # Return the token for saving
        return cls._instance.token

    @classmethod
    def reset(cls) -> None:
        """Reset the client state."""
        cls._instance = None
        cls._authenticated = False
        cls._current_email = None


async def get_monarch() -> AsyncGenerator[MonarchMoney, None]:
    """FastAPI dependency to get authenticated MonarchMoney client."""
    client = await MonarchClient.get_client()
    yield client
