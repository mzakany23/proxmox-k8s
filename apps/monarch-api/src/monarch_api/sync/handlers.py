"""Sync handlers for each entity type."""

import logging
from datetime import datetime
from decimal import Decimal

from monarchmoney import MonarchMoney
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repositories import (
    AccountRepository,
    CategoryGroupRepository,
    CategoryRepository,
    RecurringTransactionRepository,
    SyncStatusRepository,
    TagRepository,
    TransactionRepository,
    TransactionSplitRepository,
    TransactionTagRepository,
)

logger = logging.getLogger(__name__)


def parse_decimal(value: str | float | int | None) -> Decimal:
    """Parse a value to Decimal."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string."""
    if not value:
        return None
    try:
        # Handle ISO format with timezone
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Handle date only
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


class BaseSyncHandler:
    """Base sync handler."""

    entity_type: str = ""

    def __init__(self, session: AsyncSession, monarch: MonarchMoney):
        self.session = session
        self.monarch = monarch
        self.status_repo = SyncStatusRepository(session)

    async def sync(self) -> int:
        """Sync data from Monarch API to database. Returns record count."""
        raise NotImplementedError


class CategoryGroupSyncHandler(BaseSyncHandler):
    """Sync handler for category groups."""

    entity_type = "category_groups"

    async def sync(self, prefetched_data: dict | None = None) -> int:
        """Sync category groups.

        Args:
            prefetched_data: Optional pre-fetched category data to avoid duplicate API calls.
        """
        await self.status_repo.update_status(self.entity_type, "syncing")

        try:
            # Use prefetched data or fetch from API
            if prefetched_data is not None:
                data = prefetched_data
            else:
                data = await self.monarch.get_transaction_categories()
            categories = data.get("categories", [])

            # Extract unique groups
            groups_seen = set()
            groups = []
            for cat in categories:
                group = cat.get("group", {})
                if group and group.get("id") not in groups_seen:
                    groups_seen.add(group["id"])
                    groups.append({
                        "id": group["id"],
                        "name": group.get("name", ""),
                        "type": group.get("type", "expense"),
                    })

            repo = CategoryGroupRepository(self.session)
            count = await repo.upsert_many(groups)

            await self.status_repo.update_status(self.entity_type, "success", count)
            logger.info(f"Synced {count} category groups")
            return count

        except Exception as e:
            logger.exception("Failed to sync category groups")
            await self.status_repo.update_status(
                self.entity_type, "error", error_message=str(e)
            )
            raise


class CategorySyncHandler(BaseSyncHandler):
    """Sync handler for categories."""

    entity_type = "categories"

    async def sync(self, prefetched_data: dict | None = None) -> int:
        """Sync categories.

        Args:
            prefetched_data: Optional pre-fetched category data to avoid duplicate API calls.
        """
        await self.status_repo.update_status(self.entity_type, "syncing")

        try:
            # Use prefetched data or fetch from API
            if prefetched_data is not None:
                data = prefetched_data
            else:
                data = await self.monarch.get_transaction_categories()
            raw_categories = data.get("categories", [])

            categories = []
            for cat in raw_categories:
                categories.append({
                    "id": cat["id"],
                    "name": cat.get("name", ""),
                    "icon": cat.get("icon"),
                    "is_system": cat.get("isSystemCategory", False),
                    "is_hidden": cat.get("isHiddenFromBudget", False),
                    "group_id": cat.get("group", {}).get("id"),
                })

            repo = CategoryRepository(self.session)
            count = await repo.upsert_many(categories)

            await self.status_repo.update_status(self.entity_type, "success", count)
            logger.info(f"Synced {count} categories")
            return count

        except Exception as e:
            logger.exception("Failed to sync categories")
            await self.status_repo.update_status(
                self.entity_type, "error", error_message=str(e)
            )
            raise


class TagSyncHandler(BaseSyncHandler):
    """Sync handler for tags."""

    entity_type = "tags"

    async def sync(self) -> int:
        """Sync tags."""
        await self.status_repo.update_status(self.entity_type, "syncing")

        try:
            data = await self.monarch.get_transaction_tags()
            raw_tags = data.get("householdTransactionTags", [])

            tags = []
            for i, tag in enumerate(raw_tags):
                tags.append({
                    "id": tag["id"],
                    "name": tag.get("name", ""),
                    "color": tag.get("color"),
                    "order": tag.get("order", i),
                })

            repo = TagRepository(self.session)
            count = await repo.upsert_many(tags)

            await self.status_repo.update_status(self.entity_type, "success", count)
            logger.info(f"Synced {count} tags")
            return count

        except Exception as e:
            logger.exception("Failed to sync tags")
            await self.status_repo.update_status(
                self.entity_type, "error", error_message=str(e)
            )
            raise


class AccountSyncHandler(BaseSyncHandler):
    """Sync handler for accounts."""

    entity_type = "accounts"

    async def sync(self) -> int:
        """Sync accounts."""
        await self.status_repo.update_status(self.entity_type, "syncing")

        try:
            data = await self.monarch.get_accounts()
            raw_accounts = data.get("accounts", [])

            accounts = []
            for acc in raw_accounts:
                # Extract credential info if available
                credential = acc.get("credential", {}) or {}
                institution = credential.get("institution", {}) or {}

                accounts.append({
                    "id": acc["id"],
                    "display_name": acc.get("displayName"),
                    "account_type": acc.get("type", {}).get("name", "other"),
                    "account_subtype": acc.get("subtype", {}).get("name") if acc.get("subtype") else None,
                    "current_balance": parse_decimal(acc.get("currentBalance")),
                    "display_balance": parse_decimal(acc.get("displayBalance")),
                    "include_in_net_worth": acc.get("includeInNetWorth", True),
                    "hide_from_list": acc.get("hideFromList", False),
                    "is_manual": acc.get("isManual", False),
                    "is_hidden": acc.get("isHidden", False),
                    "is_deleted": acc.get("isDeleted", False),
                    "is_asset": acc.get("isAsset", True),
                    "data_provider": credential.get("dataProvider"),
                    "data_provider_id": acc.get("dataProviderAccountId"),
                    "institution_name": institution.get("name"),
                    "institution_logo": institution.get("logo"),
                    "created_at": parse_datetime(acc.get("createdAt")),
                    "updated_at": parse_datetime(acc.get("updatedAt")),
                })

            repo = AccountRepository(self.session)
            count = await repo.upsert_many(accounts)

            await self.status_repo.update_status(self.entity_type, "success", count)
            logger.info(f"Synced {count} accounts")
            return count

        except Exception as e:
            logger.exception("Failed to sync accounts")
            await self.status_repo.update_status(
                self.entity_type, "error", error_message=str(e)
            )
            raise


class TransactionSyncHandler(BaseSyncHandler):
    """Sync handler for transactions."""

    entity_type = "transactions"
    BATCH_SIZE = 500  # Fetch in smaller batches to avoid timeout

    async def sync(self, limit: int = 10000) -> int:
        """Sync transactions with pagination to avoid timeouts."""
        await self.status_repo.update_status(self.entity_type, "syncing")

        try:
            # Fetch transactions in batches
            all_transactions: list[dict] = []
            offset = 0

            while True:
                batch_limit = min(self.BATCH_SIZE, limit - len(all_transactions))
                if batch_limit <= 0:
                    break

                logger.info(f"Fetching transactions batch: offset={offset}, limit={batch_limit}")
                data = await self.monarch.get_transactions(limit=batch_limit, offset=offset)
                batch = data.get("allTransactions", {}).get("results", [])

                if not batch:
                    break

                all_transactions.extend(batch)
                offset += len(batch)

                # Stop if we got fewer than requested (no more data)
                if len(batch) < batch_limit:
                    break

            logger.info(f"Fetched {len(all_transactions)} total transactions")
            raw_transactions = all_transactions

            transactions = []
            tag_mappings: dict[str, list[str]] = {}
            split_mappings: dict[str, list[dict]] = {}

            for txn in raw_transactions:
                txn_id = txn["id"]
                category = txn.get("category", {}) or {}

                transactions.append({
                    "id": txn_id,
                    "date": parse_datetime(txn.get("date")),
                    "amount": parse_decimal(txn.get("amount")),
                    "merchant_name": txn.get("merchant", {}).get("name") if txn.get("merchant") else txn.get("plaidName"),
                    "notes": txn.get("notes"),
                    "pending": txn.get("pending", False),
                    "is_recurring": txn.get("isRecurring", False),
                    "has_attachments": bool(txn.get("attachments")),
                    "hide_from_reports": txn.get("hideFromReports", False),
                    "needs_review": txn.get("needsReview", False),
                    "plaid_name": txn.get("plaidName"),
                    "is_split": txn.get("isSplitTransaction", False),
                    "account_id": txn.get("account", {}).get("id"),
                    "category_id": category.get("id"),
                    "created_at": parse_datetime(txn.get("createdAt")),
                    "updated_at": parse_datetime(txn.get("updatedAt")),
                })

                # Collect tags
                tags = txn.get("tags", [])
                if tags:
                    tag_mappings[txn_id] = [t["id"] for t in tags]

                # Collect splits
                splits = txn.get("splitTransactions", [])
                if splits:
                    split_mappings[txn_id] = [
                        {
                            "id": s["id"],
                            "amount": parse_decimal(s.get("amount")),
                            "category_id": s.get("category", {}).get("id") if s.get("category") else None,
                            "merchant_name": s.get("merchant", {}).get("name") if s.get("merchant") else None,
                            "notes": s.get("notes"),
                        }
                        for s in splits
                    ]

            # Upsert transactions
            txn_repo = TransactionRepository(self.session)
            count = await txn_repo.upsert_many(transactions)

            # Update tags
            tag_repo = TransactionTagRepository(self.session)
            await tag_repo.bulk_replace(tag_mappings)

            # Update splits
            split_repo = TransactionSplitRepository(self.session)
            await split_repo.bulk_replace(split_mappings)

            await self.status_repo.update_status(self.entity_type, "success", count)
            logger.info(f"Synced {count} transactions")
            return count

        except Exception as e:
            logger.exception("Failed to sync transactions")
            await self.status_repo.update_status(
                self.entity_type, "error", error_message=str(e)
            )
            raise


class RecurringTransactionSyncHandler(BaseSyncHandler):
    """Sync handler for recurring transactions."""

    entity_type = "recurring_transactions"

    async def sync(self) -> int:
        """Sync recurring transactions."""
        await self.status_repo.update_status(self.entity_type, "syncing")

        try:
            data = await self.monarch.get_recurring_transactions()

            recurring = []
            for stream_type in ["outgoingStreams", "incomingStreams"]:
                is_income = stream_type == "incomingStreams"
                for item in data.get(stream_type, []):
                    account = item.get("account", {}) or {}
                    category = item.get("category", {}) or {}

                    recurring.append({
                        "id": item["id"],
                        "name": item.get("name", ""),
                        "amount": parse_decimal(item.get("amount")),
                        "frequency": item.get("frequency", "monthly"),
                        "next_date": parse_datetime(item.get("nextExpectedDate")),
                        "last_date": parse_datetime(item.get("lastTransactionDate")),
                        "is_income": is_income,
                        "is_active": item.get("isActive", True),
                        "category_id": category.get("id"),
                        "account_id": account.get("id"),
                    })

            repo = RecurringTransactionRepository(self.session)
            count = await repo.upsert_many(recurring)

            await self.status_repo.update_status(self.entity_type, "success", count)
            logger.info(f"Synced {count} recurring transactions")
            return count

        except Exception as e:
            logger.exception("Failed to sync recurring transactions")
            await self.status_repo.update_status(
                self.entity_type, "error", error_message=str(e)
            )
            raise
