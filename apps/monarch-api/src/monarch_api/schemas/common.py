"""Shared enums and common schemas."""

from enum import Enum

from pydantic import BaseModel, Field


class AccountTypeName(str, Enum):
    """Account type enumeration matching Monarch Money types."""

    BROKERAGE = "brokerage"
    CHECKING = "checking"
    CREDIT = "credit"
    DEPOSITORY = "depository"
    INVESTMENT = "investment"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OTHER = "other"
    SAVINGS = "savings"


class PaginationParams(BaseModel):
    """Common pagination parameters."""

    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class DateRange(BaseModel):
    """Date range for filtering."""

    start_date: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="End date (YYYY-MM-DD)")


class MoneyAmount(BaseModel):
    """Monetary amount with currency."""

    amount: str = Field(description="Amount as string to preserve decimal precision")
    currency: str = Field(default="USD", description="Currency code")
