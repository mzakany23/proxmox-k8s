"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Category Groups table
    op.create_table(
        "category_groups",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("is_system", sa.Boolean(), default=False),
        sa.Column("is_hidden", sa.Boolean(), default=False),
        sa.Column(
            "group_id",
            sa.String(50),
            sa.ForeignKey("category_groups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_categories_group_id", "categories", ["group_id"])

    # Tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("order", sa.Integer(), default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Accounts table
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("account_subtype", sa.String(50), nullable=True),
        sa.Column("current_balance", sa.Numeric(19, 4), default=0),
        sa.Column("display_balance", sa.Numeric(19, 4), default=0),
        sa.Column("include_in_net_worth", sa.Boolean(), default=True),
        sa.Column("hide_from_list", sa.Boolean(), default=False),
        sa.Column("is_manual", sa.Boolean(), default=False),
        sa.Column("is_hidden", sa.Boolean(), default=False),
        sa.Column("is_deleted", sa.Boolean(), default=False),
        sa.Column("is_asset", sa.Boolean(), default=True),
        sa.Column("data_provider", sa.String(100), nullable=True),
        sa.Column("data_provider_id", sa.String(100), nullable=True),
        sa.Column("institution_name", sa.String(200), nullable=True),
        sa.Column("institution_logo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_accounts_account_type", "accounts", ["account_type"])
    op.create_index("ix_accounts_is_hidden", "accounts", ["is_hidden"])

    # Transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("merchant_name", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("pending", sa.Boolean(), default=False),
        sa.Column("is_recurring", sa.Boolean(), default=False),
        sa.Column("has_attachments", sa.Boolean(), default=False),
        sa.Column("hide_from_reports", sa.Boolean(), default=False),
        sa.Column("needs_review", sa.Boolean(), default=False),
        sa.Column("plaid_name", sa.String(200), nullable=True),
        sa.Column("is_split", sa.Boolean(), default=False),
        sa.Column(
            "account_id",
            sa.String(50),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.String(50),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_merchant_name", "transactions", ["merchant_name"])
    op.create_index(
        "ix_transactions_date_account", "transactions", ["date", "account_id"]
    )

    # Transaction splits table
    op.create_table(
        "transaction_splits",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.String(50),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column(
            "category_id",
            sa.String(50),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("merchant_name", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Transaction tags junction table
    op.create_table(
        "transaction_tags",
        sa.Column(
            "transaction_id",
            sa.String(50),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.String(50),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Recurring transactions table
    op.create_table(
        "recurring_transactions",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("frequency", sa.String(50), nullable=False),
        sa.Column("next_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_income", sa.Boolean(), default=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column(
            "category_id",
            sa.String(50),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "account_id",
            sa.String(50),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Sync status table
    op.create_table(
        "sync_status",
        sa.Column("entity_type", sa.String(50), primary_key=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_synced", sa.Integer(), default=0),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("sync_status")
    op.drop_table("recurring_transactions")
    op.drop_table("transaction_tags")
    op.drop_table("transaction_splits")
    op.drop_table("transactions")
    op.drop_table("accounts")
    op.drop_table("tags")
    op.drop_table("categories")
    op.drop_table("category_groups")
