"""Repository layer for database operations."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Account,
    APIToken,
    Base,
    Category,
    CategoryGroup,
    Credential,
    RecurringTransaction,
    SyncStatus,
    Tag,
    Transaction,
    TransactionSplit,
    TransactionTag,
)

T = TypeVar("T", bound=Base)


class BaseRepository:
    """Base repository with common operations."""

    def __init__(self, session: AsyncSession):
        self.session = session


class CategoryGroupRepository(BaseRepository):
    """Repository for category groups."""

    async def upsert_many(self, groups: list[dict]) -> int:
        """Upsert multiple category groups."""
        if not groups:
            return 0

        stmt = insert(CategoryGroup).values(groups)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "type": stmt.excluded.type,
                "updated_at": datetime.now(),
            },
        )
        await self.session.execute(stmt)
        return len(groups)

    async def get_all(self) -> Sequence[CategoryGroup]:
        """Get all category groups."""
        result = await self.session.execute(select(CategoryGroup))
        return result.scalars().all()


class CategoryRepository(BaseRepository):
    """Repository for categories."""

    async def upsert_many(self, categories: list[dict]) -> int:
        """Upsert multiple categories."""
        if not categories:
            return 0

        stmt = insert(Category).values(categories)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "icon": stmt.excluded.icon,
                "is_system": stmt.excluded.is_system,
                "is_hidden": stmt.excluded.is_hidden,
                "group_id": stmt.excluded.group_id,
                "updated_at": datetime.now(),
            },
        )
        await self.session.execute(stmt)
        return len(categories)

    async def get_all(self, include_hidden: bool = False) -> Sequence[Category]:
        """Get all categories."""
        query = select(Category)
        if not include_hidden:
            query = query.where(Category.is_hidden == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, category_id: str) -> Category | None:
        """Get category by ID."""
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()


class TagRepository(BaseRepository):
    """Repository for tags."""

    async def upsert_many(self, tags: list[dict]) -> int:
        """Upsert multiple tags."""
        if not tags:
            return 0

        stmt = insert(Tag).values(tags)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "color": stmt.excluded.color,
                "order": stmt.excluded.order,
                "updated_at": datetime.now(),
            },
        )
        await self.session.execute(stmt)
        return len(tags)

    async def get_all(self) -> Sequence[Tag]:
        """Get all tags."""
        result = await self.session.execute(select(Tag).order_by(Tag.order))
        return result.scalars().all()


class AccountRepository(BaseRepository):
    """Repository for accounts."""

    async def upsert_many(self, accounts: list[dict]) -> int:
        """Upsert multiple accounts."""
        if not accounts:
            return 0

        stmt = insert(Account).values(accounts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "display_name": stmt.excluded.display_name,
                "account_type": stmt.excluded.account_type,
                "account_subtype": stmt.excluded.account_subtype,
                "current_balance": stmt.excluded.current_balance,
                "display_balance": stmt.excluded.display_balance,
                "include_in_net_worth": stmt.excluded.include_in_net_worth,
                "hide_from_list": stmt.excluded.hide_from_list,
                "is_manual": stmt.excluded.is_manual,
                "is_hidden": stmt.excluded.is_hidden,
                "is_deleted": stmt.excluded.is_deleted,
                "is_asset": stmt.excluded.is_asset,
                "data_provider": stmt.excluded.data_provider,
                "data_provider_id": stmt.excluded.data_provider_id,
                "institution_name": stmt.excluded.institution_name,
                "institution_logo": stmt.excluded.institution_logo,
                "updated_at": stmt.excluded.updated_at,
                "synced_at": datetime.now(),
            },
        )
        await self.session.execute(stmt)
        return len(accounts)

    async def get_all(self, include_hidden: bool = False) -> Sequence[Account]:
        """Get all accounts."""
        query = select(Account)
        if not include_hidden:
            query = query.where(Account.is_hidden == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, account_id: str) -> Account | None:
        """Get account by ID."""
        result = await self.session.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()


class TransactionRepository(BaseRepository):
    """Repository for transactions."""

    BATCH_SIZE = 100  # Insert in batches to avoid giant queries

    async def upsert_many(self, transactions: list[dict]) -> int:
        """Upsert multiple transactions in batches."""
        if not transactions:
            return 0

        total = 0
        for i in range(0, len(transactions), self.BATCH_SIZE):
            batch = transactions[i : i + self.BATCH_SIZE]
            stmt = insert(Transaction).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "date": stmt.excluded.date,
                    "amount": stmt.excluded.amount,
                    "merchant_name": stmt.excluded.merchant_name,
                    "notes": stmt.excluded.notes,
                    "pending": stmt.excluded.pending,
                    "is_recurring": stmt.excluded.is_recurring,
                    "has_attachments": stmt.excluded.has_attachments,
                    "hide_from_reports": stmt.excluded.hide_from_reports,
                    "needs_review": stmt.excluded.needs_review,
                    "plaid_name": stmt.excluded.plaid_name,
                    "is_split": stmt.excluded.is_split,
                    "account_id": stmt.excluded.account_id,
                    "category_id": stmt.excluded.category_id,
                    "updated_at": stmt.excluded.updated_at,
                    "synced_at": datetime.now(),
                },
            )
            await self.session.execute(stmt)
            total += len(batch)
        return total

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        account_id: str | None = None,
        category_id: str | None = None,
        search: str | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
    ) -> Sequence[Transaction]:
        """Get transactions with filters."""
        query = select(Transaction).order_by(Transaction.date.desc())

        if start_date:
            query = query.where(Transaction.date >= start_date)
        if end_date:
            query = query.where(Transaction.date <= end_date)
        if account_id:
            query = query.where(Transaction.account_id == account_id)
        if category_id:
            query = query.where(Transaction.category_id == category_id)
        if search:
            query = query.where(Transaction.merchant_name.ilike(f"%{search}%"))
        if min_amount is not None:
            query = query.where(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.where(Transaction.amount <= max_amount)

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, transaction_id: str) -> Transaction | None:
        """Get transaction by ID."""
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> Sequence[Transaction]:
        """Get transactions in date range."""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.date >= start_date)
            .where(Transaction.date <= end_date)
            .order_by(Transaction.date.desc())
        )
        return result.scalars().all()


class TransactionTagRepository(BaseRepository):
    """Repository for transaction tags."""

    async def replace_tags(self, transaction_id: str, tag_ids: list[str]) -> None:
        """Replace all tags for a transaction."""
        # Delete existing
        await self.session.execute(
            delete(TransactionTag).where(
                TransactionTag.transaction_id == transaction_id
            )
        )

        # Insert new
        if tag_ids:
            values = [
                {"transaction_id": transaction_id, "tag_id": tag_id}
                for tag_id in tag_ids
            ]
            await self.session.execute(insert(TransactionTag).values(values))

    async def bulk_replace(self, tag_mappings: dict[str, list[str]]) -> None:
        """Bulk replace tags for multiple transactions."""
        if not tag_mappings:
            return

        # Delete all existing tags for these transactions
        await self.session.execute(
            delete(TransactionTag).where(
                TransactionTag.transaction_id.in_(tag_mappings.keys())
            )
        )

        # Build values for insert
        values = []
        for transaction_id, tag_ids in tag_mappings.items():
            for tag_id in tag_ids:
                values.append({"transaction_id": transaction_id, "tag_id": tag_id})

        if values:
            await self.session.execute(insert(TransactionTag).values(values))


class TransactionSplitRepository(BaseRepository):
    """Repository for transaction splits."""

    async def replace_splits(self, transaction_id: str, splits: list[dict]) -> None:
        """Replace all splits for a transaction."""
        # Delete existing
        await self.session.execute(
            delete(TransactionSplit).where(
                TransactionSplit.transaction_id == transaction_id
            )
        )

        # Insert new
        if splits:
            for split in splits:
                split["transaction_id"] = transaction_id
            await self.session.execute(insert(TransactionSplit).values(splits))

    async def bulk_replace(self, split_mappings: dict[str, list[dict]]) -> None:
        """Bulk replace splits for multiple transactions."""
        if not split_mappings:
            return

        # Delete all existing splits for these transactions
        await self.session.execute(
            delete(TransactionSplit).where(
                TransactionSplit.transaction_id.in_(split_mappings.keys())
            )
        )

        # Build values for insert
        values = []
        for transaction_id, splits in split_mappings.items():
            for split in splits:
                split["transaction_id"] = transaction_id
                values.append(split)

        if values:
            await self.session.execute(insert(TransactionSplit).values(values))


class RecurringTransactionRepository(BaseRepository):
    """Repository for recurring transactions."""

    async def upsert_many(self, recurring: list[dict]) -> int:
        """Upsert multiple recurring transactions."""
        if not recurring:
            return 0

        stmt = insert(RecurringTransaction).values(recurring)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "amount": stmt.excluded.amount,
                "frequency": stmt.excluded.frequency,
                "next_date": stmt.excluded.next_date,
                "last_date": stmt.excluded.last_date,
                "is_income": stmt.excluded.is_income,
                "is_active": stmt.excluded.is_active,
                "category_id": stmt.excluded.category_id,
                "account_id": stmt.excluded.account_id,
                "updated_at": datetime.now(),
                "synced_at": datetime.now(),
            },
        )
        await self.session.execute(stmt)
        return len(recurring)

    async def get_all(self, is_active: bool | None = None) -> Sequence[RecurringTransaction]:
        """Get all recurring transactions."""
        query = select(RecurringTransaction)
        if is_active is not None:
            query = query.where(RecurringTransaction.is_active == is_active)
        result = await self.session.execute(query)
        return result.scalars().all()


class SyncStatusRepository(BaseRepository):
    """Repository for sync status."""

    async def get(self, entity_type: str) -> SyncStatus | None:
        """Get sync status for entity type."""
        result = await self.session.execute(
            select(SyncStatus).where(SyncStatus.entity_type == entity_type)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> Sequence[SyncStatus]:
        """Get all sync statuses."""
        result = await self.session.execute(select(SyncStatus))
        return result.scalars().all()

    async def update_status(
        self,
        entity_type: str,
        status: str,
        records_synced: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Update sync status for entity type."""
        now = datetime.now()

        stmt = insert(SyncStatus).values(
            entity_type=entity_type,
            status=status,
            records_synced=records_synced,
            last_sync_at=now if status == "success" else None,
            error_message=error_message,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["entity_type"],
            set_={
                "status": status,
                "records_synced": records_synced,
                "last_sync_at": now if status == "success" else SyncStatus.last_sync_at,
                "error_message": error_message,
                "updated_at": now,
            },
        )
        await self.session.execute(stmt)


class CredentialRepository(BaseRepository):
    """Repository for authentication credentials."""

    async def get_active(self) -> Credential | None:
        """Get the active credential (most recent active one)."""
        result = await self.session.execute(
            select(Credential)
            .where(Credential.is_active == True)  # noqa: E712
            .order_by(Credential.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save(self, email: str, token: str) -> Credential:
        """Save a new credential, deactivating any existing ones."""
        # Deactivate all existing credentials
        await self.session.execute(
            update(Credential).values(is_active=False)
        )

        # Insert new credential
        credential = Credential(email=email, token=token, is_active=True)
        self.session.add(credential)
        await self.session.flush()
        return credential

    async def delete_all(self) -> int:
        """Delete all credentials."""
        result = await self.session.execute(delete(Credential))
        return result.rowcount or 0

    async def deactivate_all(self) -> int:
        """Deactivate all credentials."""
        result = await self.session.execute(
            update(Credential).values(is_active=False)
        )
        return result.rowcount or 0


class APITokenRepository(BaseRepository):
    """Repository for API tokens."""

    async def create(self, token_hash: str, name: str, scope: str = "read", expires_at: datetime | None = None) -> APIToken:
        """Create a new API token."""
        token = APIToken(
            token_hash=token_hash,
            name=name,
            scope=scope,
            is_active=True,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> APIToken | None:
        """Get an API token by its hash."""
        result = await self.session.execute(
            select(APIToken).where(
                APIToken.token_hash == token_hash,
                APIToken.is_active == True,  # noqa: E712
            )
        )
        token = result.scalar_one_or_none()

        # Check expiration
        if token and token.expires_at and token.expires_at < datetime.now():
            return None

        return token

    async def get_by_id(self, token_id: int) -> APIToken | None:
        """Get an API token by ID."""
        result = await self.session.execute(
            select(APIToken).where(APIToken.id == token_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, include_inactive: bool = False) -> Sequence[APIToken]:
        """Get all API tokens."""
        query = select(APIToken).order_by(APIToken.created_at.desc())
        if not include_inactive:
            query = query.where(APIToken.is_active == True)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_last_used(self, token_id: int) -> None:
        """Update the last_used_at timestamp for a token."""
        await self.session.execute(
            update(APIToken)
            .where(APIToken.id == token_id)
            .values(last_used_at=datetime.now())
        )

    async def revoke(self, token_id: int) -> bool:
        """Revoke (deactivate) an API token."""
        result = await self.session.execute(
            update(APIToken)
            .where(APIToken.id == token_id)
            .values(is_active=False)
        )
        return (result.rowcount or 0) > 0

    async def delete(self, token_id: int) -> bool:
        """Delete an API token."""
        result = await self.session.execute(
            delete(APIToken).where(APIToken.id == token_id)
        )
        return (result.rowcount or 0) > 0
