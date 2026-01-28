"""Transaction endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from monarchmoney import MonarchMoney

from ..auth.dependencies import require_scope
from ..db.models import APIToken
from ..dependencies import get_monarch
from ..schemas.transactions import (
    Transaction,
    TransactionCreate,
    TransactionSplitCreate,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _transform_transaction(raw: dict) -> dict:
    """Transform raw transaction data to schema format."""
    category = raw.get("category", {}) or {}
    account = raw.get("account", {}) or {}
    tags = raw.get("tags", []) or []
    split_transactions = raw.get("splitTransactions", []) or []

    return {
        "id": raw.get("id"),
        "date": raw.get("date"),
        "amount": str(raw.get("amount", 0)),
        "merchant_name": raw.get("merchant", {}).get("name") if raw.get("merchant") else raw.get("plaidName"),
        "category_id": category.get("id"),
        "category_name": category.get("name"),
        "category_icon": category.get("icon"),
        "category_group": category.get("group", {}).get("name") if category.get("group") else None,
        "notes": raw.get("notes"),
        "pending": raw.get("pending", False),
        "is_recurring": raw.get("isRecurring", False),
        "has_attachments": bool(raw.get("attachments")),
        "hide_from_reports": raw.get("hideFromReports", False),
        "needs_review": raw.get("needsReview", False),
        "plaid_name": raw.get("plaidName"),
        "account_id": account.get("id"),
        "account_name": account.get("displayName"),
        "tags": [t.get("name") for t in tags if t.get("name")],
        "is_split": raw.get("isSplitTransaction", False) or len(split_transactions) > 0,
        "splits": [
            {
                "id": s.get("id"),
                "amount": str(s.get("amount", 0)),
                "category_id": s.get("category", {}).get("id") if s.get("category") else None,
                "merchant_name": s.get("merchant", {}).get("name") if s.get("merchant") else None,
                "notes": s.get("notes"),
            }
            for s in split_transactions
        ],
        "created_at": raw.get("createdAt"),
        "updated_at": raw.get("updatedAt"),
    }


@router.get("", response_model=list[Transaction])
async def list_transactions(
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    search: str | None = Query(default=None, description="Search term"),
    category_id: str | None = Query(default=None, description="Filter by category"),
    account_id: str | None = Query(default=None, description="Filter by account"),
    tag_id: str | None = Query(default=None, description="Filter by tag"),
    has_notes: bool | None = Query(default=None, description="Filter by notes"),
    needs_review: bool | None = Query(default=None, description="Filter needs review"),
) -> list[Transaction]:
    """Get transactions with optional filters."""
    kwargs = {
        "limit": limit,
        "offset": offset,
    }

    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    if search:
        kwargs["search"] = search
    if category_id:
        kwargs["category_ids"] = [category_id]
    if account_id:
        kwargs["account_ids"] = [account_id]
    if tag_id:
        kwargs["tag_ids"] = [tag_id]
    if has_notes is not None:
        kwargs["has_notes"] = has_notes
    if needs_review is not None:
        kwargs["needs_review"] = needs_review

    result = await monarch.get_transactions(**kwargs)
    transactions = result.get("allTransactions", {}).get("results", [])

    return [Transaction(**_transform_transaction(t)) for t in transactions]


@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
) -> Transaction:
    """Get a specific transaction by ID."""
    result = await monarch.get_transaction_details(transaction_id)
    transaction = result.get("getTransaction")

    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

    return Transaction(**_transform_transaction(transaction))


@router.post("", response_model=Transaction)
async def create_transaction(
    transaction: TransactionCreate,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> Transaction:
    """Create a new transaction."""
    result = await monarch.create_transaction(
        date=transaction.date.isoformat(),
        account_id=transaction.account_id,
        amount=float(transaction.amount),
        merchant_name=transaction.merchant_name or "",
        category_id=transaction.category_id,
        notes=transaction.notes,
    )

    created = result.get("createTransaction", {}).get("transaction", {})
    return Transaction(**_transform_transaction(created))


@router.patch("/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: str,
    update: TransactionUpdate,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> Transaction:
    """Update a transaction."""
    kwargs = {}

    if update.merchant_name is not None:
        kwargs["name"] = update.merchant_name
    if update.category_id is not None:
        kwargs["category_id"] = update.category_id
    if update.notes is not None:
        kwargs["notes"] = update.notes
    if update.hide_from_reports is not None:
        kwargs["hide_from_reports"] = update.hide_from_reports
    if update.needs_review is not None:
        kwargs["needs_review"] = update.needs_review

    if kwargs:
        await monarch.update_transaction(transaction_id, **kwargs)

    # Fetch and return updated transaction
    return await get_transaction(transaction_id, monarch, _)


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> dict:
    """Delete a transaction."""
    await monarch.delete_transaction(transaction_id)
    return {"message": "Transaction deleted", "id": transaction_id}


@router.post("/{transaction_id}/split", response_model=Transaction)
async def split_transaction(
    transaction_id: str,
    splits: list[TransactionSplitCreate],
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> Transaction:
    """Split a transaction into multiple parts."""
    # Convert splits to the format expected by monarchmoney
    split_data = [
        {
            "amount": float(s.amount),
            "categoryId": s.category_id,
            "merchantName": s.merchant_name,
            "notes": s.notes,
        }
        for s in splits
    ]

    await monarch.update_transaction_splits(transaction_id, split_data)

    # Fetch and return updated transaction
    return await get_transaction(transaction_id, monarch, _)


@router.post("/{transaction_id}/tags/{tag_id}")
async def add_tag_to_transaction(
    transaction_id: str,
    tag_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> dict:
    """Add a tag to a transaction."""
    await monarch.set_transaction_tags(transaction_id, [tag_id])
    return {"message": "Tag added", "transaction_id": transaction_id, "tag_id": tag_id}


@router.delete("/{transaction_id}/tags/{tag_id}")
async def remove_tag_from_transaction(
    transaction_id: str,
    tag_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> dict:
    """Remove a tag from a transaction."""
    # Get current tags
    result = await monarch.get_transaction_details(transaction_id)
    transaction = result.get("getTransaction", {})
    current_tags = [t.get("id") for t in transaction.get("tags", []) if t.get("id") != tag_id]

    await monarch.set_transaction_tags(transaction_id, current_tags)
    return {"message": "Tag removed", "transaction_id": transaction_id, "tag_id": tag_id}
