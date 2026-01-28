"""Cashflow and recurring transaction endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from monarchmoney import MonarchMoney

from ..auth.dependencies import require_scope
from ..db.models import APIToken
from ..dependencies import get_monarch
from ..schemas.cashflow import CashflowByCategory, CashflowSummary, RecurringTransaction

router = APIRouter(prefix="/cashflow", tags=["Cashflow"])


def _transform_recurring(raw: dict) -> dict:
    """Transform raw recurring transaction data to schema format."""
    stream = raw.get("stream", {}) or {}
    category = stream.get("category", {}) or {}
    account = raw.get("account", {}) or {}

    return {
        "id": raw.get("id"),
        "name": stream.get("name") or raw.get("name", "Unknown"),
        "amount": str(stream.get("amount", 0)),
        "frequency": stream.get("frequency", "monthly"),
        "next_date": raw.get("nextForecastedDate"),
        "last_date": raw.get("lastDate"),
        "category_id": category.get("id"),
        "category_name": category.get("name"),
        "account_id": account.get("id"),
        "account_name": account.get("displayName"),
        "is_income": stream.get("isIncome", False),
        "is_active": raw.get("isActive", True),
    }


@router.get("/summary", response_model=CashflowSummary)
async def get_cashflow_summary(
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> CashflowSummary:
    """Get cashflow summary for a time period."""
    # Default to current month
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).isoformat()
    if not end_date:
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1).isoformat()
        else:
            end_date = today.replace(month=today.month + 1, day=1).isoformat()

    result = await monarch.get_cashflow(start_date=start_date, end_date=end_date)
    cashflow = result.get("cashFlow", {})

    # Calculate totals
    summary = cashflow.get("summary", {}) or {}
    total_income = float(summary.get("sumIncome", 0))
    total_expenses = float(summary.get("sumExpense", 0))
    net = total_income + total_expenses  # expenses are negative

    savings_rate = None
    if total_income > 0:
        savings_rate = f"{(net / total_income * 100):.1f}"

    # Breakdown by category
    by_category = []
    for cat_data in cashflow.get("byCategory", []):
        category = cat_data.get("category", {}) or {}
        by_category.append(
            CashflowByCategory(
                category_id=category.get("id", ""),
                category_name=category.get("name", "Unknown"),
                category_icon=category.get("icon"),
                category_group=category.get("group", {}).get("name") if category.get("group") else None,
                amount=str(cat_data.get("amount", 0)),
                transaction_count=cat_data.get("count", 0),
            )
        )

    return CashflowSummary(
        start_date=start_date,
        end_date=end_date,
        total_income=str(total_income),
        total_expenses=str(abs(total_expenses)),
        net_cashflow=str(net),
        savings_rate=savings_rate,
        by_category=by_category,
    )


@router.get("/recurring", response_model=list[RecurringTransaction])
async def list_recurring_transactions(
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
    include_inactive: bool = Query(default=False, description="Include inactive recurring transactions"),
) -> list[RecurringTransaction]:
    """Get recurring transactions."""
    result = await monarch.get_recurring_transactions()
    recurring = result.get("recurringTransactionStreams", [])

    transactions = []
    for item in recurring:
        transformed = _transform_recurring(item)
        if include_inactive or transformed.get("is_active", True):
            transactions.append(RecurringTransaction(**transformed))

    return transactions


@router.get("/recurring/{recurring_id}", response_model=RecurringTransaction)
async def get_recurring_transaction(
    recurring_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
) -> RecurringTransaction:
    """Get a specific recurring transaction."""
    result = await monarch.get_recurring_transactions()
    recurring = result.get("recurringTransactionStreams", [])

    for item in recurring:
        if item.get("id") == recurring_id:
            return RecurringTransaction(**_transform_recurring(item))

    raise HTTPException(status_code=404, detail=f"Recurring transaction {recurring_id} not found")
