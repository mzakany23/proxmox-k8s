"""CLI for Monarch Money authentication.

Provides interactive login with MFA support and saves credentials to .env file.
"""

import argparse
import asyncio
import getpass
import os
import re
from pathlib import Path

from monarchmoney import MonarchMoney
from monarchmoney.monarchmoney import MonarchMoneyEndpoints, RequireMFAException

# Patch the base URL
MonarchMoneyEndpoints.BASE_URL = "https://api.monarch.com"


def find_env_file() -> Path:
    """Find the .env file, searching up from cwd."""
    cwd = Path.cwd()

    # Check current directory first
    env_path = cwd / ".env"
    if env_path.exists():
        return env_path

    # Check parent directories
    for parent in cwd.parents:
        env_path = parent / ".env"
        if env_path.exists():
            return env_path

    # Default to current directory
    return cwd / ".env"


def read_env_file(env_path: Path) -> dict[str, str]:
    """Read existing .env file into a dictionary."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=VALUE
                match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
                if match:
                    key, value = match.groups()
                    # Remove surrounding quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    env_vars[key] = value
    return env_vars


def update_env_file(env_path: Path, updates: dict[str, str]) -> None:
    """Update .env file with new values, preserving existing content.

    Args:
        env_path: Path to .env file
        updates: Dictionary of key-value pairs to add/update
    """
    lines = []
    updated_keys = set()

    # Read existing file and update in place
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                original_line = line
                line_stripped = line.strip()

                # Check if this line is a key we need to update
                for key, value in updates.items():
                    if line_stripped.startswith(f"{key}="):
                        # Quote value if it contains special characters
                        if any(c in value for c in [' ', '"', "'", '#', '$']):
                            line = f'{key}="{value}"\n'
                        else:
                            line = f"{key}={value}\n"
                        updated_keys.add(key)
                        break

                lines.append(line if line != original_line else original_line)

    # Append any new keys that weren't updated
    for key, value in updates.items():
        if key not in updated_keys:
            if any(c in value for c in [' ', '"', "'", '#', '$']):
                lines.append(f'{key}="{value}"\n')
            else:
                lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, "w") as f:
        f.writelines(lines)

    # Set restrictive permissions (owner read/write only)
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass  # May fail on Windows


async def interactive_login(
    email: str | None = None,
    password: str | None = None,
) -> tuple[MonarchMoney, str, str]:
    """Perform interactive login with MFA support.

    Args:
        email: Email address (will prompt if not provided)
        password: Password (will prompt if not provided)

    Returns:
        Tuple of (authenticated client, token, email)
    """
    client = MonarchMoney()

    # Prompt for credentials if not provided
    if not email:
        email = input("Email: ").strip()
    if not password:
        password = getpass.getpass("Password: ")

    print(f"\nLogging in as {email}...")

    try:
        # Never save session pickle - we use token-based auth
        await client.login(
            email=email,
            password=password,
            use_saved_session=False,
            save_session=False,
        )
    except RequireMFAException:
        print("\nMFA required. Check your authenticator app.")
        mfa_code = input("MFA Code: ").strip()

        await client.multi_factor_authenticate(email, password, mfa_code)

    token = client.token
    if not token:
        raise RuntimeError("Login succeeded but no token received")

    print("Login successful!")
    return client, token, email


async def refresh_login(email: str) -> tuple[MonarchMoney, str, str]:
    """Re-login using saved email (prompts for password and MFA).

    Args:
        email: Saved email address

    Returns:
        Tuple of (authenticated client, token, email)
    """
    print(f"\nRefreshing login for {email}...")
    return await interactive_login(email=email, password=None)


def main():
    """CLI entry point for monarch-login."""
    parser = argparse.ArgumentParser(
        description="Log in to Monarch Money and save token to .env",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  monarch-login              # Interactive login, saves token to .env
  monarch-login --refresh    # Re-login using saved email (prompts for password + MFA)
  monarch-login --no-save    # Don't save anything to .env
        """,
    )
    parser.add_argument(
        "--refresh", "-r",
        action="store_true",
        help="Re-login using saved email from .env (prompts for password + MFA)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save token to .env file",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Path to .env file (default: searches up from cwd)",
    )

    args = parser.parse_args()

    # Find or use specified .env file
    env_path = args.env_file or find_env_file()
    env_vars = read_env_file(env_path)

    if args.refresh:
        # Use saved email, prompt for password
        email = env_vars.get("MONARCH_EMAIL")

        if not email:
            print("Error: No saved email found in .env file.")
            print("Run 'monarch-login' without --refresh first.")
            return 1

        client, token, email = asyncio.run(refresh_login(email=email))
    else:
        # Interactive login, pre-fill email if saved
        email = env_vars.get("MONARCH_EMAIL")
        client, token, email = asyncio.run(interactive_login(email=email))

    # Save to .env
    if not args.no_save:
        updates = {
            "MONARCH_TOKEN": token,
            "MONARCH_EMAIL": email,
        }

        update_env_file(env_path, updates)
        print(f"\nSaved to {env_path}:")
        print(f"  MONARCH_TOKEN=<{len(token)} chars>")
        print(f"  MONARCH_EMAIL={email}")

    print("\nYou can now use monarch-api, monarch-export, etc.")
    return 0


if __name__ == "__main__":
    exit(main() or 0)
