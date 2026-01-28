"""SQLAlchemy ORM models for monarch-api."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class CategoryGroup(Base):
    """Category group model."""

    __tablename__ = "category_groups"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # expense, income, transfer
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    categories: Mapped[list["Category"]] = relationship(back_populates="group")


class Category(Base):
    """Category model."""

    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(100))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    group_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("category_groups.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    group: Mapped[CategoryGroup | None] = relationship(back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category")

    __table_args__ = (Index("ix_categories_group_id", "group_id"),)


class Tag(Base):
    """Tag model."""

    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(String(20))
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    transaction_tags: Mapped[list["TransactionTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class Account(Base):
    """Account model."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    account_subtype: Mapped[str | None] = mapped_column(String(50))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=Decimal("0"))
    display_balance: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=Decimal("0"))
    include_in_net_worth: Mapped[bool] = mapped_column(Boolean, default=True)
    hide_from_list: Mapped[bool] = mapped_column(Boolean, default=False)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_asset: Mapped[bool] = mapped_column(Boolean, default=True)
    data_provider: Mapped[str | None] = mapped_column(String(100))
    data_provider_id: Mapped[str | None] = mapped_column(String(100))
    institution_name: Mapped[str | None] = mapped_column(String(200))
    institution_logo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
    recurring_transactions: Mapped[list["RecurringTransaction"]] = relationship(
        back_populates="account"
    )

    __table_args__ = (
        Index("ix_accounts_account_type", "account_type"),
        Index("ix_accounts_is_hidden", "is_hidden"),
    )


class Transaction(Base):
    """Transaction model."""

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    pending: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    hide_from_reports: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    plaid_name: Mapped[str | None] = mapped_column(String(200))
    is_split: Mapped[bool] = mapped_column(Boolean, default=False)

    # Foreign keys
    account_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("categories.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    account: Mapped[Account] = relationship(back_populates="transactions")
    category: Mapped[Category | None] = relationship(back_populates="transactions")
    splits: Mapped[list["TransactionSplit"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    transaction_tags: Mapped[list["TransactionTag"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_category_id", "category_id"),
        Index("ix_transactions_merchant_name", "merchant_name"),
        Index("ix_transactions_date_account", "date", "account_id"),
    )


class TransactionSplit(Base):
    """Transaction split model."""

    __tablename__ = "transaction_splits"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    category_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("categories.id", ondelete="SET NULL")
    )
    merchant_name: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    transaction: Mapped[Transaction] = relationship(back_populates="splits")


class TransactionTag(Base):
    """Many-to-many relationship between transactions and tags."""

    __tablename__ = "transaction_tags"

    transaction_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    transaction: Mapped[Transaction] = relationship(back_populates="transaction_tags")
    tag: Mapped[Tag] = relationship(back_populates="transaction_tags")


class RecurringTransaction(Base):
    """Recurring transaction model."""

    __tablename__ = "recurring_transactions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    frequency: Mapped[str] = mapped_column(String(50), nullable=False)
    next_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_income: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Foreign keys
    category_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("categories.id", ondelete="SET NULL")
    )
    account_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("accounts.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    account: Mapped[Account | None] = relationship(back_populates="recurring_transactions")


class SyncStatus(Base):
    """Track sync status for each entity type."""

    __tablename__ = "sync_status"

    entity_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_synced: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, syncing, success, error
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Credential(Base):
    """Store authentication credentials for Monarch API."""

    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class APIToken(Base):
    """API tokens for HTTP API authentication."""

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="read")  # read, write, admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
