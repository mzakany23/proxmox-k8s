"""Abstract base class for Excel sheets."""

from abc import ABC, abstractmethod

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from ..config import ReportConfig
from ..data_loader import LoadedData
from ..formatters import ExcelFormatter, auto_width


class BaseSheet(ABC):
    """Abstract base class for Excel sheet generators."""

    # Sheet identifier used in config
    sheet_id: str = ""

    # Display name for the Excel tab
    sheet_name: str = ""

    def __init__(self, config: ReportConfig, data: LoadedData, styles: dict):
        self.config = config
        self.data = data
        self.styles = styles
        self.formatter = ExcelFormatter

    @abstractmethod
    def can_generate(self) -> tuple[bool, str]:
        """Check if this sheet can be generated with available data.

        Returns:
            Tuple of (can_generate, reason_if_not)
        """
        pass

    @abstractmethod
    def generate(self, wb: Workbook) -> Worksheet:
        """Generate the sheet in the workbook.

        Args:
            wb: The workbook to add the sheet to

        Returns:
            The created worksheet
        """
        pass

    def _create_sheet(self, wb: Workbook) -> Worksheet:
        """Create a new worksheet with the sheet name."""
        return wb.create_sheet(title=self.sheet_name)

    def _auto_width(self, ws: Worksheet) -> None:
        """Auto-adjust column widths."""
        auto_width(ws)
