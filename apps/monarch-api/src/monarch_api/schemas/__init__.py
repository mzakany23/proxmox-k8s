"""Pydantic schemas for the Monarch Money API."""

from .accounts import Account, AccountCreate, AccountUpdate, AccountHolding, AccountHistory
from .auth import LoginRequest, LoginResponse, MFARequest, AuthStatus
from .budgets import Budget, BudgetItem, BudgetItemUpdate
from .cashflow import CashflowSummary, RecurringTransaction, CashflowByCategory
from .categories import Category, Tag, TagCreate
from .common import AccountTypeName, PaginationParams
from .transactions import (
    Transaction,
    TransactionCreate,
    TransactionUpdate,
    TransactionFilters,
    TransactionSplit,
)

__all__ = [
    # Common
    "AccountTypeName",
    "PaginationParams",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "MFARequest",
    "AuthStatus",
    # Accounts
    "Account",
    "AccountCreate",
    "AccountUpdate",
    "AccountHolding",
    "AccountHistory",
    # Transactions
    "Transaction",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionFilters",
    "TransactionSplit",
    # Categories
    "Category",
    "Tag",
    "TagCreate",
    # Budgets
    "Budget",
    "BudgetItem",
    "BudgetItemUpdate",
    # Cashflow
    "CashflowSummary",
    "RecurringTransaction",
    "CashflowByCategory",
]
