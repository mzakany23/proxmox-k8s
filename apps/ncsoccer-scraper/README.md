# NC Soccer Scraper

CLI tool to track Key West FC across NC Soccer Hudson leagues.

## Installation

```bash
uv venv && uv pip install -e .
source .venv/bin/activate
```

## Usage

```bash
# Show all upcoming games across all leagues
soccer upcoming

# Show standings for all leagues
soccer standings

# Show standings for a specific league
soccer standings --league sunday

# Show recent results
soccer results

# Show full schedule for a specific league
soccer schedule --league friday

# Refresh/verify data
soccer refresh

# Show configuration
soccer info
```

## Leagues Tracked

| League | Day | Team ID |
|--------|-----|---------|
| Mens Open B | Tuesday | 3190980 |
| Mens 40+ Friday | Friday | 3188350 |
| Mens 30+ Sunday | Sunday | 3189947 |

## Configuration

The tool looks for `config.yaml` in:
1. Current directory
2. `~/.config/ncsoccer/config.yaml`

If no config is found, it uses the default Key West FC configuration.
