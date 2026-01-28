"""Account-related schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .common import AccountTypeName


class AccountBase(BaseModel):
    """Base account fields."""

    display_name: str | None = Field(default=None, description="Display name for the account")
    include_in_net_worth: bool = Field(default=True, description="Include in net worth calculations")
    hide_from_list: bool = Field(default=False, description="Hide from account list")


class AccountCreate(AccountBase):
    """Schema for creating a manual account."""

    account_type: AccountTypeName = Field(description="Type of account")
    account_subtype: str | None = Field(default=None, description="Account subtype")
    current_balance: Decimal = Field(default=Decimal("0"), description="Current balance")


class AccountUpdate(BaseModel):
    """Schema for updating an account."""

    display_name: str | None = Field(default=None, description="Display name for the account")
    include_in_net_worth: bool | None = Field(default=None, description="Include in net worth calculations")
    hide_from_list: bool | None = Field(default=None, description="Hide from account list")
    current_balance: Decimal | None = Field(default=None, description="Current balance (manual accounts only)")


class Account(AccountBase):
    """Full account representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique account identifier")
    account_type: str = Field(description="Type of account")
    account_subtype: str | None = Field(default=None, description="Account subtype")
    current_balance: str = Field(description="Current balance as string")
    display_balance: str = Field(description="Display balance as string")
    is_manual: bool = Field(default=False, description="Whether this is a manual account")
    is_hidden: bool = Field(default=False, description="Whether account is hidden")
    is_deleted: bool = Field(default=False, description="Whether account is deleted")
    is_asset: bool = Field(default=True, description="Whether account is an asset")
    data_provider: str | None = Field(default=None, description="Data provider name")
    data_provider_id: str | None = Field(default=None, description="Data provider account ID")
    institution_name: str | None = Field(default=None, description="Financial institution name")
    institution_logo: str | None = Field(default=None, description="Institution logo URL")
    created_at: datetime | None = Field(default=None, description="Account creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class AccountHolding(BaseModel):
    """Investment holding within an account."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Holding identifier")
    name: str = Field(description="Security name")
    ticker: str | None = Field(default=None, description="Ticker symbol")
    quantity: str = Field(description="Number of shares/units")
    price: str = Field(description="Current price per share")
    value: str = Field(description="Total value")
    cost_basis: str | None = Field(default=None, description="Cost basis")
    holding_type: str | None = Field(default=None, description="Type of holding")


class AccountHistory(BaseModel):
    """Historical account balance snapshot."""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(description="Date of snapshot (YYYY-MM-DD)")
    balance: str = Field(description="Balance on this date")
