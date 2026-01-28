"""CLI tools for Monarch API administration."""

import asyncio
import hashlib
import secrets
import sys
from datetime import datetime, timedelta

from sqlalchemy import select

from .config import settings
from .db.engine import AsyncSessionLocal
from .db.models import APIToken
from .db.repositories import APITokenRepository


async def _create_token(
    name: str,
    scope: str = "admin",
    expires_in_days: int | None = None,
) -> tuple[str, APIToken]:
    """Create an API token in the database."""
    if not settings.has_database:
        raise RuntimeError("DATABASE_URL not configured")

    # Generate token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now() + timedelta(days=expires_in_days)

    async with AsyncSessionLocal() as session:
        repo = APITokenRepository(session)
        token = await repo.create(
            token_hash=token_hash,
            name=name,
            scope=scope,
            expires_at=expires_at,
        )
        await session.commit()
        # Refresh to get the ID
        await session.refresh(token)

    return raw_token, token


async def _list_tokens() -> list[APIToken]:
    """List all API tokens."""
    if not settings.has_database:
        raise RuntimeError("DATABASE_URL not configured")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(APIToken).order_by(APIToken.created_at.desc())
        )
        return list(result.scalars().all())


async def _revoke_token(token_id: int) -> bool:
    """Revoke an API token by ID."""
    if not settings.has_database:
        raise RuntimeError("DATABASE_URL not configured")

    async with AsyncSessionLocal() as session:
        repo = APITokenRepository(session)
        success = await repo.revoke(token_id)
        await session.commit()
        return success


def create_admin_token(
    name: str = "admin",
    expires_in_days: int | None = None,
) -> None:
    """Create an admin API token for bootstrapping.

    The token value is printed to stdout and should be saved securely.
    It cannot be retrieved again.

    Args:
        name: Name for the token (default: "admin")
        expires_in_days: Days until expiration (default: never expires)
    """
    try:
        raw_token, token = asyncio.run(_create_token(name, "admin", expires_in_days))
        print(f"\nAdmin token created successfully!")
        print(f"  ID: {token.id}")
        print(f"  Name: {token.name}")
        print(f"  Scope: {token.scope}")
        if token.expires_at:
            print(f"  Expires: {token.expires_at.isoformat()}")
        else:
            print(f"  Expires: Never")
        print(f"\n  Token: {raw_token}")
        print(f"\n  IMPORTANT: Save this token securely. It cannot be retrieved again!")
        print(f"\n  Usage: curl -H 'Authorization: Bearer {raw_token}' http://localhost:8000/accounts")
    except Exception as e:
        print(f"Error creating token: {e}", file=sys.stderr)
        sys.exit(1)


def list_tokens() -> None:
    """List all API tokens."""
    try:
        tokens = asyncio.run(_list_tokens())
        if not tokens:
            print("No API tokens found.")
            return

        print(f"\nAPI Tokens ({len(tokens)} total):")
        print("-" * 80)
        for t in tokens:
            status = "active" if t.is_active else "revoked"
            expires = t.expires_at.isoformat() if t.expires_at else "never"
            last_used = t.last_used_at.isoformat() if t.last_used_at else "never"
            print(f"  ID: {t.id}")
            print(f"    Name: {t.name}")
            print(f"    Scope: {t.scope}")
            print(f"    Status: {status}")
            print(f"    Created: {t.created_at.isoformat()}")
            print(f"    Expires: {expires}")
            print(f"    Last used: {last_used}")
            print()
    except Exception as e:
        print(f"Error listing tokens: {e}", file=sys.stderr)
        sys.exit(1)


def revoke_token(token_id: int) -> None:
    """Revoke an API token by ID.

    Args:
        token_id: The ID of the token to revoke
    """
    try:
        success = asyncio.run(_revoke_token(token_id))
        if success:
            print(f"Token {token_id} revoked successfully.")
        else:
            print(f"Token {token_id} not found.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error revoking token: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Monarch API administration tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-token command
    create_parser = subparsers.add_parser(
        "create-token",
        help="Create a new API token",
    )
    create_parser.add_argument(
        "--name",
        default="admin",
        help="Name for the token (default: admin)",
    )
    create_parser.add_argument(
        "--scope",
        choices=["read", "write", "admin"],
        default="admin",
        help="Token scope (default: admin)",
    )
    create_parser.add_argument(
        "--expires-in-days",
        type=int,
        default=None,
        help="Days until expiration (default: never)",
    )

    # list-tokens command
    subparsers.add_parser(
        "list-tokens",
        help="List all API tokens",
    )

    # revoke-token command
    revoke_parser = subparsers.add_parser(
        "revoke-token",
        help="Revoke an API token",
    )
    revoke_parser.add_argument(
        "token_id",
        type=int,
        help="ID of the token to revoke",
    )

    args = parser.parse_args()

    if args.command == "create-token":
        raw_token, token = asyncio.run(
            _create_token(args.name, args.scope, args.expires_in_days)
        )
        print(f"\nAPI token created successfully!")
        print(f"  ID: {token.id}")
        print(f"  Name: {token.name}")
        print(f"  Scope: {token.scope}")
        if token.expires_at:
            print(f"  Expires: {token.expires_at.isoformat()}")
        else:
            print(f"  Expires: Never")
        print(f"\n  Token: {raw_token}")
        print(f"\n  IMPORTANT: Save this token securely. It cannot be retrieved again!")
        print(f"\n  Usage: curl -H 'Authorization: Bearer {raw_token}' http://localhost:8000/accounts")
    elif args.command == "list-tokens":
        list_tokens()
    elif args.command == "revoke-token":
        revoke_token(args.token_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
