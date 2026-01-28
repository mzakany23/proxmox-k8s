"""Budget-related schemas."""

from pydantic import BaseModel, ConfigDict, Field


class BudgetItem(BaseModel):
    """A single budget item for a category."""

    model_config = ConfigDict(from_attributes=True)

    category_id: str = Field(description="Category identifier")
    category_name: str = Field(description="Category name")
    category_icon: str | None = Field(default=None, description="Category icon")
    category_group: str | None = Field(default=None, description="Category group name")
    budgeted_amount: str = Field(description="Budgeted amount")
    actual_amount: str = Field(description="Actual spent amount")
    remaining_amount: str = Field(description="Remaining budget")
    is_flexible: bool = Field(default=False, description="Whether budget is flexible")
    rollover_enabled: bool = Field(default=False, description="Whether rollover is enabled")
    rollover_amount: str | None = Field(default=None, description="Rollover amount from previous period")


class BudgetItemUpdate(BaseModel):
    """Schema for updating a budget item."""

    amount: str = Field(description="New budgeted amount")
    apply_to_future: bool = Field(default=False, description="Apply to future months")


class BudgetSummary(BaseModel):
    """Summary totals for a budget period."""

    total_budgeted: str = Field(description="Total budgeted amount")
    total_actual: str = Field(description="Total actual spending")
    total_remaining: str = Field(description="Total remaining")
    income_budgeted: str = Field(description="Budgeted income")
    income_actual: str = Field(description="Actual income")


class Budget(BaseModel):
    """Full budget for a time period."""

    model_config = ConfigDict(from_attributes=True)

    start_date: str = Field(description="Budget period start (YYYY-MM-DD)")
    end_date: str = Field(description="Budget period end (YYYY-MM-DD)")
    summary: BudgetSummary = Field(description="Budget summary totals")
    items: list[BudgetItem] = Field(default_factory=list, description="Budget line items")
