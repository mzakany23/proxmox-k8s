# Monarch Money API

A FastAPI REST API wrapper for [Monarch Money](https://www.monarchmoney.com/), providing CLI tools and a clean HTTP interface to your financial data.

## Quick Start

```bash
git clone https://github.com/yourusername/monarch-api.git
cd monarch-api
uv sync
monarch-login        # Authenticate (handles MFA)
monarch-export       # Export all data to CSV
```

## Features

- **CLI Tools**: `monarch-login`, `monarch-export`, `monarch-report`, `monarch-api`
- **REST API**: Full HTTP interface to Monarch Money data
- **Excel Reports**: Financial summaries with charts and formatting
- **CSV Export**: Bulk export of all financial data
- **Claude Code Skill**: Query your finances using natural language

## Claude Code Integration

This project includes a [Claude Code](https://github.com/anthropics/claude-code) skill that lets you query your Monarch Money data using natural language.

### How It Works

When working in this project directory, Claude Code automatically discovers the skill at `.claude/skills/monarch/`. Use the `/monarch` command to interact with your financial data:

```
/monarch show my account balances
/monarch what did I spend on groceries last month?
/monarch generate a financial report for Q4
/monarch export my data to CSV
```

### Global Installation

To use the skill across all your projects:

```bash
# Create the global skills directory if it doesn't exist
mkdir -p ~/.claude/skills

# Symlink or copy the skill
ln -s /path/to/monarch-api/.claude/skills/monarch ~/.claude/skills/monarch
# OR
cp -r /path/to/monarch-api/.claude/skills/monarch ~/.claude/skills/
```

After installation, `/monarch` will be available in any project.

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Monarch Money account

### Install

```bash
cd monarch-api
uv sync
```

## Authentication

### Option 1: CLI Login (Recommended)

The easiest way to authenticate:

```bash
monarch-login
```

This will:
1. Prompt for your email and password
2. Handle MFA code entry automatically
3. Save your token to `.env`

To refresh your token using saved credentials (only prompts for MFA):

```bash
monarch-login --refresh
```

### Option 2: Manual Token Extraction

If you prefer to extract the token manually:

1. Log in to [app.monarchmoney.com](https://app.monarchmoney.com)
2. Open browser DevTools (F12) → Network tab
3. Find any request to `api.monarch.com`
4. Copy the `Authorization` header value (without "Token ")

Create a `.env` file:

```bash
MONARCH_TOKEN=your_token_here
```

## CLI Tools

### `monarch-login` - Authenticate with Monarch Money

```bash
monarch-login              # Interactive login, saves token + email to .env
monarch-login --refresh    # Re-login using saved email (prompts for password + MFA)
monarch-login --no-save    # Don't save to .env
```

### `monarch-export` - Export Data to CSV

Export all your financial data to CSV files:

```bash
monarch-export             # Export to timestamped directory
monarch-export -o ./data   # Export to specific directory
```

Exports:
- `accounts.csv` - All linked accounts and balances
- `transactions.csv` - Complete transaction history
- `categories.csv` - Transaction categories
- `tags.csv` - Custom tags
- `recurring_transactions.csv` - Recurring transaction streams
- `cashflow_summary.csv` - Monthly income/expense summary

### `monarch-report` - Generate Excel Financial Report

```bash
# First export data
monarch-export -o ./data

# Generate report with defaults (last 6 months)
monarch-report -i ./data

# Custom date range
monarch-report -i ./data --start-date 2024-01-01 --end-date 2024-12-31

# Last 12 months
monarch-report -i ./data --months 12

# Select specific sheets
monarch-report -i ./data --sheets summary monthly categories

# Custom output path
monarch-report -i ./data -o quarterly-report.xlsx
```

**Generated sheets:**
1. **Summary** - Dashboard with totals, top categories, top merchants, account balances
2. **Monthly Spending** - Pivot table by category/month with heat map
3. **Categories** - Hierarchical breakdown (group type > group > category)
4. **Accounts** - Balances and inflow/outflow per account
5. **Transactions** - Filterable transaction list

### `monarch-api` - Start REST API Server

```bash
monarch-api                # Start on localhost:8000
monarch-api --port 3000    # Custom port
monarch-api --host 0.0.0.0 # Bind to all interfaces
monarch-api --reload       # Enable auto-reload for development
```

Visit http://localhost:8000/docs for the interactive Swagger UI.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /auth/status` | Authentication status |
| `GET /accounts` | List all accounts |
| `GET /transactions` | List transactions (with filters) |
| `GET /categories` | List categories |
| `GET /tags` | List tags |
| `GET /cashflow/summary` | Monthly cashflow summary |
| `GET /cashflow/recurring` | Recurring transactions |
| `GET /budgets` | Budget data |

### Transaction Filters

```bash
# Filter by date range
curl "http://localhost:8000/transactions?start_date=2024-01-01&end_date=2024-12-31"

# Filter by account
curl "http://localhost:8000/transactions?account_id=12345"

# Search
curl "http://localhost:8000/transactions?search=grocery"

# Pagination
curl "http://localhost:8000/transactions?limit=50&offset=100"
```

## Running Tests

```bash
uv run pytest
```

## Project Structure

```
monarch-api/
├── src/monarch_api/
│   ├── main.py           # FastAPI app
│   ├── config.py         # Settings from environment
│   ├── dependencies.py   # MonarchMoney client singleton
│   ├── export.py         # CSV export functionality
│   ├── report.py         # Excel report generation
│   ├── login.py          # Authentication CLI
│   ├── routers/          # API endpoint routers
│   │   ├── accounts.py
│   │   ├── transactions.py
│   │   ├── categories.py
│   │   ├── budgets.py
│   │   └── cashflow.py
│   └── schemas/          # Pydantic models
├── .claude/skills/monarch/  # Claude Code skill
├── tests/
├── pyproject.toml
└── .env                  # Your token (not committed)
```

## Known Issues

- The official Monarch Money library needed patches for:
  - Domain change: `api.monarchmoney.com` → `api.monarch.com`
  - gql library compatibility: requires `gql<4.0.0`
  - Token auth: must pass token to constructor, not `set_token()`

## Security

- Never commit your `.env` file or token
- CSV exports contain sensitive financial data - store securely
- Token expires periodically - use `monarch-login --refresh` when needed
