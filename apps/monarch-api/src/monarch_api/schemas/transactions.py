"""Transaction-related schemas."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionSplit(BaseModel):
    """A split portion of a transaction."""

    id: str | None = Field(default=None, description="Split identifier")
    amount: str = Field(description="Split amount")
    category_id: str | None = Field(default=None, description="Category for this split")
    merchant_name: str | None = Field(default=None, description="Merchant name override")
    notes: str | None = Field(default=None, description="Notes for this split")


class TransactionSplitCreate(BaseModel):
    """Schema for creating a transaction split."""

    amount: str = Field(description="Split amount")
    category_id: str | None = Field(default=None, description="Category for this split")
    merchant_name: str | None = Field(default=None, description="Merchant name override")
    notes: str | None = Field(default=None, description="Notes for this split")


class TransactionBase(BaseModel):
    """Base transaction fields."""

    date: datetime.date = Field(description="Transaction date")
    merchant_name: str | None = Field(default=None, description="Merchant name")
    category_id: str | None = Field(default=None, description="Category ID")
    notes: str | None = Field(default=None, description="Transaction notes")


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction."""

    account_id: str = Field(description="Account ID for this transaction")
    amount: str = Field(description="Transaction amount (negative for debits)")


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""

    date: datetime.date | None = Field(default=None, description="Transaction date")
    merchant_name: str | None = Field(default=None, description="Merchant name")
    category_id: str | None = Field(default=None, description="Category ID")
    notes: str | None = Field(default=None, description="Transaction notes")
    hide_from_reports: bool | None = Field(default=None, description="Hide from reports")
    needs_review: bool | None = Field(default=None, description="Mark as needs review")


class Transaction(TransactionBase):
    """Full transaction representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique transaction identifier")
    amount: str = Field(description="Transaction amount")
    pending: bool = Field(default=False, description="Whether transaction is pending")
    is_recurring: bool = Field(default=False, description="Whether this is recurring")
    has_attachments: bool = Field(default=False, description="Whether attachments exist")
    hide_from_reports: bool = Field(default=False, description="Hidden from reports")
    needs_review: bool = Field(default=False, description="Needs user review")
    plaid_name: str | None = Field(default=None, description="Original name from Plaid")

    # Account info
    account_id: str = Field(description="Account ID")
    account_name: str | None = Field(default=None, description="Account display name")

    # Category info
    category_name: str | None = Field(default=None, description="Category name")
    category_icon: str | None = Field(default=None, description="Category icon")
    category_group: str | None = Field(default=None, description="Category group name")

    # Tags
    tags: list[str] = Field(default_factory=list, description="Applied tag names")

    # Splits
    is_split: bool = Field(default=False, description="Whether transaction is split")
    splits: list[TransactionSplit] = Field(default_factory=list, description="Split details")

    created_at: datetime.datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime.datetime | None = Field(default=None, description="Last update timestamp")


class TransactionFilters(BaseModel):
    """Filters for transaction queries."""

    limit: int = Field(default=100, ge=1, le=1000, description="Max results")
    offset: int = Field(default=0, ge=0, description="Results to skip")
    start_date: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="End date (YYYY-MM-DD)")
    search: str | None = Field(default=None, description="Search term")
    category_id: str | None = Field(default=None, description="Filter by category")
    account_id: str | None = Field(default=None, description="Filter by account")
    tag_id: str | None = Field(default=None, description="Filter by tag")
    has_attachments: bool | None = Field(default=None, description="Filter by attachments")
    has_notes: bool | None = Field(default=None, description="Filter by notes")
    is_recurring: bool | None = Field(default=None, description="Filter recurring")
    needs_review: bool | None = Field(default=None, description="Filter needs review")
    hide_from_reports: bool | None = Field(default=None, description="Filter hidden")
