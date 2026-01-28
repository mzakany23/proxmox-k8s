"""Exception handlers for the API."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gql.transport.exceptions import TransportQueryError


class MonarchAPIError(Exception):
    """Base exception for Monarch API errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(MonarchAPIError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class MFARequiredError(MonarchAPIError):
    """MFA verification required."""

    def __init__(self, message: str = "Multi-factor authentication required"):
        super().__init__(message, status_code=403)


async def monarch_api_error_handler(request: Request, exc: MonarchAPIError) -> JSONResponse:
    """Handle Monarch API errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def transport_error_handler(request: Request, exc: TransportQueryError) -> JSONResponse:
    """Handle GraphQL transport errors from monarchmoney."""
    error_message = str(exc)

    # Check for authentication-related errors
    if "unauthorized" in error_message.lower() or "authentication" in error_message.lower():
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication failed. Check your credentials."},
        )

    # Check for MFA errors
    if "mfa" in error_message.lower() or "multi-factor" in error_message.lower():
        return JSONResponse(
            status_code=403,
            content={"detail": "Multi-factor authentication required.", "mfa_required": True},
        )

    # Generic API error
    return JSONResponse(
        status_code=502,
        content={"detail": f"Monarch Money API error: {error_message}"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(MonarchAPIError, monarch_api_error_handler)
    app.add_exception_handler(TransportQueryError, transport_error_handler)
