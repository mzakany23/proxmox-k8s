"""Report configuration."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class ReportConfig:
    """Configuration for Excel report generation."""

    export_dir: Path
    output_path: Path | None = None
    start_date: date | None = None
    end_date: date | None = None
    months_back: int = 6
    sheets: list[str] = field(default_factory=lambda: ["summary", "monthly", "categories", "accounts", "transactions"])
    exclude_transfers: bool = True
    exclude_hidden: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize configuration."""
        self.export_dir = Path(self.export_dir)
        if self.output_path:
            self.output_path = Path(self.output_path)

    @property
    def all_sheets(self) -> list[str]:
        """Get list of all available sheet types."""
        return ["summary", "monthly", "categories", "accounts", "transactions"]
