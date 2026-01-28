"""CSV data loading with graceful missing data handling."""

from dataclasses import dataclass, field
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path

import pandas as pd

from .config import ReportConfig


@dataclass
class LoadedData:
    """Container for loaded CSV data with availability tracking."""

    transactions: pd.DataFrame | None = None
    accounts: pd.DataFrame | None = None
    categories: pd.DataFrame | None = None
    tags: pd.DataFrame | None = None
    recurring: pd.DataFrame | None = None
    cashflow: pd.DataFrame | None = None

    missing_files: list[str] = field(default_factory=list)
    available_files: list[str] = field(default_factory=list)

    @property
    def has_transactions(self) -> bool:
        return self.transactions is not None and not self.transactions.empty

    @property
    def has_accounts(self) -> bool:
        return self.accounts is not None and not self.accounts.empty

    @property
    def has_categories(self) -> bool:
        return self.categories is not None and not self.categories.empty

    @property
    def has_tags(self) -> bool:
        return self.tags is not None and not self.tags.empty

    @property
    def has_recurring(self) -> bool:
        return self.recurring is not None and not self.recurring.empty

    @property
    def has_cashflow(self) -> bool:
        return self.cashflow is not None and not self.cashflow.empty


class DataLoader:
    """Load CSV exports with graceful handling of missing files."""

    CSV_FILES = {
        "transactions": "transactions.csv",
        "accounts": "accounts.csv",
        "categories": "categories.csv",
        "tags": "tags.csv",
        "recurring": "recurring_transactions.csv",
        "cashflow": "cashflow_summary.csv",
    }

    def __init__(self, config: ReportConfig):
        self.config = config
        self.data = LoadedData()

    def load(self) -> LoadedData:
        """Load all available CSV files."""
        for data_type, filename in self.CSV_FILES.items():
            filepath = self.config.export_dir / filename
            if filepath.exists():
                df = self._load_csv(filepath, data_type)
                setattr(self.data, data_type, df)
                self.data.available_files.append(filename)
            else:
                self.data.missing_files.append(filename)

        self._apply_date_filter()
        self._apply_exclusion_filters()

        return self.data

    def _load_csv(self, filepath: Path, data_type: str) -> pd.DataFrame:
        """Load a CSV file with appropriate type handling."""
        df = pd.read_csv(filepath)

        if data_type == "transactions":
            df["date"] = pd.to_datetime(df["date"])
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

        if data_type == "accounts":
            df["current_balance"] = pd.to_numeric(df["current_balance"], errors="coerce")

        if data_type == "cashflow":
            df["month"] = pd.to_datetime(df["month"])
            for col in ["income", "expenses", "savings"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def _apply_date_filter(self) -> None:
        """Apply date range filtering to transactions."""
        if self.data.transactions is None:
            return

        df = self.data.transactions

        # Determine date range
        if self.config.start_date and self.config.end_date:
            start = pd.Timestamp(self.config.start_date)
            end = pd.Timestamp(self.config.end_date)
        else:
            # Use months_back from latest transaction
            latest = df["date"].max()
            end = latest
            start = pd.Timestamp(latest.to_pydatetime() - relativedelta(months=self.config.months_back))

        # Constrain to available data range
        data_min = df["date"].min()
        data_max = df["date"].max()
        start = max(start, data_min)
        end = min(end, data_max)

        self.data.transactions = df[(df["date"] >= start) & (df["date"] <= end)].copy()

        # Store effective date range for reporting
        self.data.effective_start = start.date() if hasattr(start, "date") else start
        self.data.effective_end = end.date() if hasattr(end, "date") else end

    def _apply_exclusion_filters(self) -> None:
        """Apply transfer and hidden account exclusions."""
        if self.data.transactions is None:
            return

        df = self.data.transactions

        if self.config.exclude_hidden:
            df = df[df["hide_from_reports"] != True]

        if self.config.exclude_transfers:
            # Exclude transfer categories
            transfer_keywords = ["transfer", "payment"]
            if "category_group" in df.columns:
                # Fill NaN values and convert to string before string operations
                mask = df["category_group"].fillna("").astype(str).str.lower().isin(transfer_keywords)
            else:
                mask = pd.Series(False, index=df.index)
            df = df[~mask]

        self.data.transactions = df

    def get_date_range(self) -> tuple[date, date]:
        """Get the effective date range of loaded data."""
        if hasattr(self.data, "effective_start"):
            return self.data.effective_start, self.data.effective_end
        return date.today(), date.today()
