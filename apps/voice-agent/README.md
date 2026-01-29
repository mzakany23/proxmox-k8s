# Voice Agent

A voice interface to Claude with tool calling support. Talk to your data using natural voice conversation.

## Architecture

```
┌──────────────┐     WebRTC      ┌─────────────────────────────────────┐
│ Your Browser │◄───────────────►│ Voice Agent Server                  │
│ (mic/speaker)│                 │                                     │
└──────────────┘                 │  Deepgram ──► Claude ──► Cartesia   │
                                 │     STT         │         TTS       │
                                 │                 │                   │
                                 │         ┌───────▼───────┐           │
                                 │         │ Tools         │           │
                                 │         │ • Finances    │           │
                                 │         │ • K8s status  │           │
                                 │         │ • (your MCP)  │           │
                                 │         └───────────────┘           │
                                 └─────────────────────────────────────┘
```

## Quick Start

### 1. Get API Keys (all have free tiers)

| Service | Purpose | Get Key |
|---------|---------|---------|
| Anthropic | LLM (Claude) | https://console.anthropic.com/ |
| Deepgram | Speech-to-Text | https://console.deepgram.com/ |
| Cartesia | Text-to-Speech | https://play.cartesia.ai/ |
| Daily.co | WebRTC Transport | https://dashboard.daily.co/ |

### 2. Configure

```bash
cd /Users/michaelzakany/projects/proxmox/apps/voice-agent
cp env.example .env
# Edit .env and add your API keys
```

### 3. Install & Run

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and run
uv sync
uv run bot.py
```

### 4. Talk to it

Open the Daily room URL printed in the terminal in your browser. Grant microphone access and start talking!

## Available Tools (Stubbed)

The bot currently has these tools with stub implementations:

| Tool | Description |
|------|-------------|
| `get_account_balances` | Get financial account balances |
| `get_spending_by_category` | Spending breakdown by category |
| `search_transactions` | Search transactions by merchant |
| `get_cluster_status` | Kubernetes cluster health |
| `get_current_time` | Current date/time |

## Connecting Real MCP Tools

To connect to your actual MCP servers, you have two options:

### Option A: Direct API Calls (Simpler)

Replace the stub implementations with actual API calls:

```python
async def get_account_balances(params: FunctionCallParams):
    async with aiohttp.ClientSession() as session:
        # Call your Monarch Money MCP server
        async with session.post(
            "http://localhost:8080/tools/get_account_balances",
            json={}
        ) as resp:
            result = await resp.json()
            # Format for voice...
```

### Option B: MCP Client Integration (Full Featured)

Use the official MCP Python SDK to connect to your MCP servers:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def connect_mcp():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "your_mcp_server"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Now you can call tools
            result = await session.call_tool("get_account_balances", {})
```

## Example Conversations

Once running, try these:

- "What's my net worth?"
- "How much did I spend on groceries this month?"
- "Search for Amazon transactions"
- "How's my cluster doing?"
- "What time is it?"

## Troubleshooting

### "Missing API keys"
Make sure your `.env` file has all required keys.

### No audio / can't hear bot
- Check browser microphone permissions
- Try a different browser (Chrome works best)
- Check that your speakers are working

### High latency
- Expected latency is 300-600ms
- If higher, try a different Deepgram model or check your network

## Cost Estimates

| Service | Free Tier | Paid Rate |
|---------|-----------|-----------|
| Anthropic | None (pay as you go) | ~$3/M input, $15/M output |
| Deepgram | $200 credit | $0.0043/min |
| Cartesia | 500 chars/request free | $0.15/1K chars |
| Daily.co | 10K min/month | $0.004/min |

For casual testing: ~$0.01-0.05 per conversation
