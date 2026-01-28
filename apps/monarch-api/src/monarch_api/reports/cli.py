"""CLI entry point for Excel report generation."""

import argparse
from datetime import date, datetime
from pathlib import Path

from .config import ReportConfig
from .generator import ExcelReportGenerator


def parse_date(date_str: str) -> date:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.") from e


def main() -> None:
    """CLI entry point for monarch-report command."""
    parser = argparse.ArgumentParser(
        description="Generate Excel financial reports from Monarch Money CSV exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 6-month report (default)
  monarch-report -i ./export

  # Custom date range
  monarch-report -i ./export --start-date 2025-07-01 --end-date 2026-01-23

  # Last 12 months
  monarch-report -i ./export --months 12

  # Specific sheets only
  monarch-report -i ./export --sheets summary monthly

  # Custom output file
  monarch-report -i ./export -o report.xlsx
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Directory containing Monarch Money CSV exports",
        dest="export_dir",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output Excel file path (default: monarch_report_TIMESTAMP.xlsx in export dir)",
        dest="output_path",
    )

    parser.add_argument(
        "--months",
        type=int,
        default=6,
        help="Number of months to include (default: 6)",
        dest="months_back",
    )

    parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Start date (YYYY-MM-DD). Overrides --months",
    )

    parser.add_argument(
        "--end-date",
        type=parse_date,
        help="End date (YYYY-MM-DD). Defaults to today",
    )

    parser.add_argument(
        "--sheets",
        nargs="+",
        choices=["summary", "monthly", "categories", "accounts", "transactions"],
        default=["summary", "monthly", "categories", "accounts", "transactions"],
        help="Sheets to include (default: all)",
    )

    parser.add_argument(
        "--include-transfers",
        action="store_true",
        help="Include transfer transactions (default: exclude)",
    )

    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden accounts/transactions (default: exclude)",
    )

    args = parser.parse_args()

    # Validate export directory
    if not args.export_dir.exists():
        parser.error(f"Export directory not found: {args.export_dir}")

    if not args.export_dir.is_dir():
        parser.error(f"Not a directory: {args.export_dir}")

    # Check for required files
    transactions_file = args.export_dir / "transactions.csv"
    if not transactions_file.exists():
        parser.error(f"transactions.csv not found in {args.export_dir}")

    # Create config
    config = ReportConfig(
        export_dir=args.export_dir,
        output_path=args.output_path,
        start_date=args.start_date,
        end_date=args.end_date,
        months_back=args.months_back,
        sheets=args.sheets,
        exclude_transfers=not args.include_transfers,
        exclude_hidden=not args.include_hidden,
    )

    print(f"Generating Excel report from {args.export_dir}")
    print()

    # Generate report
    generator = ExcelReportGenerator(config)
    output_path = generator.generate()

    print()
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
