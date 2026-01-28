"""Cashflow and recurring transaction schemas."""

from pydantic import BaseModel, ConfigDict, Field


class CashflowByCategory(BaseModel):
    """Cashflow breakdown by category."""

    model_config = ConfigDict(from_attributes=True)

    category_id: str = Field(description="Category identifier")
    category_name: str = Field(description="Category name")
    category_icon: str | None = Field(default=None, description="Category icon")
    category_group: str | None = Field(default=None, description="Category group name")
    amount: str = Field(description="Total amount for this category")
    transaction_count: int = Field(default=0, description="Number of transactions")


class CashflowSummary(BaseModel):
    """Cashflow summary for a time period."""

    model_config = ConfigDict(from_attributes=True)

    start_date: str = Field(description="Period start (YYYY-MM-DD)")
    end_date: str = Field(description="Period end (YYYY-MM-DD)")
    total_income: str = Field(description="Total income")
    total_expenses: str = Field(description="Total expenses")
    net_cashflow: str = Field(description="Net cashflow (income - expenses)")
    savings_rate: str | None = Field(default=None, description="Savings rate percentage")
    by_category: list[CashflowByCategory] = Field(
        default_factory=list, description="Breakdown by category"
    )


class RecurringTransaction(BaseModel):
    """A recurring transaction pattern."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Recurring transaction identifier")
    name: str = Field(description="Transaction name/merchant")
    amount: str = Field(description="Expected amount")
    frequency: str = Field(description="Frequency (monthly, weekly, etc.)")
    next_date: str | None = Field(default=None, description="Next expected date")
    last_date: str | None = Field(default=None, description="Last occurrence date")
    category_id: str | None = Field(default=None, description="Category ID")
    category_name: str | None = Field(default=None, description="Category name")
    account_id: str | None = Field(default=None, description="Account ID")
    account_name: str | None = Field(default=None, description="Account name")
    is_income: bool = Field(default=False, description="Whether this is income")
    is_active: bool = Field(default=True, description="Whether still active")


class RecurringTransactionUpdate(BaseModel):
    """Schema for updating a recurring transaction."""

    name: str | None = Field(default=None, description="Transaction name")
    amount: str | None = Field(default=None, description="Expected amount")
    category_id: str | None = Field(default=None, description="Category ID")
    is_active: bool | None = Field(default=None, description="Whether active")
