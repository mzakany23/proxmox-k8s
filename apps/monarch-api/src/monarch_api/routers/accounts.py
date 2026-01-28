"""Account endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from monarchmoney import MonarchMoney

from ..auth.dependencies import require_scope
from ..db.models import APIToken
from ..dependencies import get_monarch
from ..schemas.accounts import Account, AccountHistory, AccountHolding, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["Accounts"])


def _transform_account(raw: dict) -> dict:
    """Transform raw account data to schema format."""
    return {
        "id": raw.get("id"),
        "display_name": raw.get("displayName"),
        "account_type": raw.get("type", {}).get("name") if isinstance(raw.get("type"), dict) else raw.get("type"),
        "account_subtype": raw.get("subtype", {}).get("name") if isinstance(raw.get("subtype"), dict) else raw.get("subtype"),
        "current_balance": str(raw.get("currentBalance", 0)),
        "display_balance": str(raw.get("displayBalance", raw.get("currentBalance", 0))),
        "include_in_net_worth": raw.get("includeInNetWorth", True),
        "hide_from_list": raw.get("hideFromList", False),
        "is_manual": raw.get("isManual", False),
        "is_hidden": raw.get("isHidden", False),
        "is_deleted": raw.get("isDeleted", False),
        "is_asset": raw.get("isAsset", True),
        "data_provider": raw.get("credential", {}).get("dataProvider") if raw.get("credential") else None,
        "data_provider_id": raw.get("credential", {}).get("id") if raw.get("credential") else None,
        "institution_name": raw.get("institution", {}).get("name") if raw.get("institution") else None,
        "institution_logo": raw.get("logoUrl") or (raw.get("institution", {}).get("logo") if raw.get("institution") else None),
        "created_at": raw.get("createdAt"),
        "updated_at": raw.get("updatedAt"),
    }


@router.get("", response_model=list[Account])
async def list_accounts(
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
    include_hidden: bool = Query(default=False, description="Include hidden accounts"),
) -> list[Account]:
    """Get all accounts."""
    result = await monarch.get_accounts()
    accounts = result.get("accounts", [])

    if not include_hidden:
        accounts = [a for a in accounts if not a.get("isHidden", False)]

    return [Account(**_transform_account(a)) for a in accounts]


@router.get("/{account_id}", response_model=Account)
async def get_account(
    account_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
) -> Account:
    """Get a specific account by ID."""
    result = await monarch.get_accounts()
    accounts = result.get("accounts", [])

    for account in accounts:
        if account.get("id") == account_id:
            return Account(**_transform_account(account))

    raise HTTPException(status_code=404, detail=f"Account {account_id} not found")


@router.patch("/{account_id}", response_model=Account)
async def update_account(
    account_id: str,
    update: AccountUpdate,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> Account:
    """Update an account's settings."""
    # Build update kwargs
    kwargs = {}
    if update.display_name is not None:
        kwargs["name"] = update.display_name
    if update.include_in_net_worth is not None:
        kwargs["includeInNetWorth"] = update.include_in_net_worth
    if update.hide_from_list is not None:
        kwargs["hideFromList"] = update.hide_from_list

    if kwargs:
        await monarch.update_account(account_id, **kwargs)

    # If balance update for manual account
    if update.current_balance is not None:
        await monarch.update_account_balance(
            account_id=account_id,
            balance=float(update.current_balance),
        )

    # Fetch and return updated account
    return await get_account(account_id, monarch, _)


@router.post("/{account_id}/refresh")
async def refresh_account(
    account_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("write"))],
) -> dict:
    """Trigger a refresh for a linked account."""
    # Get account to find credential ID
    result = await monarch.get_accounts()
    accounts = result.get("accounts", [])

    account = None
    for a in accounts:
        if a.get("id") == account_id:
            account = a
            break

    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    credential = account.get("credential")
    if not credential or not credential.get("id"):
        raise HTTPException(status_code=400, detail="Account is not a linked account")

    await monarch.request_accounts_refresh(credential["id"])
    return {"message": "Account refresh requested", "account_id": account_id}


@router.get("/{account_id}/holdings", response_model=list[AccountHolding])
async def get_account_holdings(
    account_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
) -> list[AccountHolding]:
    """Get investment holdings for an account."""
    result = await monarch.get_account_holdings()
    holdings = result.get("portfolio", {}).get("holdings", [])

    # Filter to this account
    account_holdings = [h for h in holdings if h.get("account", {}).get("id") == account_id]

    return [
        AccountHolding(
            id=h.get("id", ""),
            name=h.get("security", {}).get("name", "Unknown"),
            ticker=h.get("security", {}).get("ticker"),
            quantity=str(h.get("quantity", 0)),
            price=str(h.get("security", {}).get("currentPrice", 0)),
            value=str(h.get("value", 0)),
            cost_basis=str(h.get("costBasis")) if h.get("costBasis") is not None else None,
            holding_type=h.get("security", {}).get("type"),
        )
        for h in account_holdings
    ]


@router.get("/{account_id}/history", response_model=list[AccountHistory])
async def get_account_history(
    account_id: str,
    monarch: Annotated[MonarchMoney, Depends(get_monarch)],
    _: Annotated[APIToken, Depends(require_scope("read"))],
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> list[AccountHistory]:
    """Get historical balance data for an account."""
    result = await monarch.get_account_history(account_id)
    snapshots = result.get("accountHistory", {}).get("snapshots", [])

    history = []
    for snapshot in snapshots:
        date_str = snapshot.get("date")
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue
        history.append(
            AccountHistory(
                date=date_str,
                balance=str(snapshot.get("balance", 0)),
            )
        )

    return history
