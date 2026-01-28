"""Budget endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from monarchmoney import MonarchMoney

from ..auth.dependencies import require_scope
from ..db.models import APIToken
from ..dependencies import get_monarch
from ..schemas.budgets import Budget, BudgetItem, BudgetItemUpdate, BudgetSummary

router = APIRouter(prefix="/budgets", tags=["Budgets"])


def _transform_budget_item(raw: dict) -> dict:
    """Transform raw budget item data to schema format."""
    category = raw.get("category", {}) or {}
    planned = raw.get("plannedCashFlowAmount", {}) or {}

    return {
        "category_id": category.get("id"),
        "category_name": category.get("name", "Unknown"),
        "category_icon": category.get("icon"),
        "category_group": category.get("group", {}).get("name") if category.get("group") else None,
        "budgeted_amount": str(planned.get("amount", 0)),
        "actual_amount": str(raw.get("actualCashFlow", {}).get("amount", 0)),
        "remaining_amount": str(raw.get("remainingAmount", 0)),
        "is_flexible": raw.get("isFlexibleBudget", False),
        "rollover_enabled": raw.get("rolloverEnabled", False),
        "rollover_amount": str(raw.get("rolloverAmount", 0)) if raw.get("rolloverAmount") else None,
    }


@router.get("", response_model=Budget)
async def get_budget(
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD), defaults to current month"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD), defaults to current month"),
) -> Budget:
    """Get budget for a time period."""
    # Default to current month if not specified
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).isoformat()
    if not end_date:
        # Last day of current month
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1).isoformat()
        else:
            end_date = today.replace(month=today.month + 1, day=1).isoformat()

    result = await monarch.get_budgets(start_date=start_date, end_date=end_date)
    budget_data = result.get("budgetData", {})

    # Extract totals
    totals = budget_data.get("totalsByMonth", [{}])[0] if budget_data.get("totalsByMonth") else {}

    summary = BudgetSummary(
        total_budgeted=str(totals.get("plannedExpenses", 0)),
        total_actual=str(totals.get("actualExpenses", 0)),
        total_remaining=str(totals.get("remainingExpenses", 0)),
        income_budgeted=str(totals.get("plannedIncome", 0)),
        income_actual=str(totals.get("actualIncome", 0)),
    )

    # Extract budget items
    items_raw = budget_data.get("monthlyAmountsByCategory", [])
    items = [BudgetItem(**_transform_budget_item(item)) for item in items_raw]

    return Budget(
        start_date=start_date,
        end_date=end_date,
        summary=summary,
        items=items,
    )


@router.patch("/items/{category_id}", response_model=BudgetItem)
async def update_budget_item(
    category_id: str,
    update: BudgetItemUpdate,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
    start_date: str | None = Query(default=None, description="Budget month start date"),
) -> BudgetItem:
    """Update a budget item for a category."""
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).isoformat()

    await monarch.update_budget_item(
        category_id=category_id,
        amount=float(update.amount),
        start_date=start_date,
        apply_to_future=update.apply_to_future,
    )

    # Fetch updated budget and find the item
    budget = await get_budget(
        monarch,
        _,
        start_date=start_date,
        end_date=start_date,  # Same day for single month
    )

    for item in budget.items:
        if item.category_id == category_id:
            return item

    # Return a default item if not found
    return BudgetItem(
        category_id=category_id,
        category_name="Unknown",
        budgeted_amount=update.amount,
        actual_amount="0",
        remaining_amount=update.amount,
    )
