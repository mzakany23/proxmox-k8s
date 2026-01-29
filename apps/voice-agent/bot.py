"""
Voice Agent - A voice interface to Claude with tool calling support.

This bot uses:
- Deepgram for speech-to-text
- Claude (Anthropic) for the LLM with tool calling
- Cartesia for text-to-speech
- Daily.co for WebRTC transport (browser-based audio)

Run with: uv run bot.py
Then open: http://localhost:7860
"""

import asyncio
import os
import sys
from datetime import datetime

import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.anthropic.llm import AnthropicLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.llm_service import FunctionCallParams, FunctionSchema
from pipecat.transports.services.daily import DailyParams, DailyTransport

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


# =============================================================================
# TOOL DEFINITIONS - Stub implementations for your MCP tools
# =============================================================================

async def get_account_balances(params: FunctionCallParams):
    """Get all account balances from Monarch Money."""
    logger.info("Tool called: get_account_balances")

    # TODO: Replace with actual MCP call to monarch-money
    # result = await mcp_client.call_tool("mcp__monarch-money__get_account_balances", {})

    # Stub response
    result = {
        "total_assets": 125000.00,
        "total_liabilities": 15000.00,
        "net_worth": 110000.00,
        "accounts": [
            {"name": "Checking", "balance": 5200.00, "type": "checking"},
            {"name": "Savings", "balance": 25000.00, "type": "savings"},
            {"name": "Investment", "balance": 94800.00, "type": "brokerage"},
            {"name": "Credit Card", "balance": -1500.00, "type": "credit"},
        ]
    }

    # Format for voice response
    response = f"Your net worth is ${result['net_worth']:,.2f}. "
    response += f"You have ${result['total_assets']:,.2f} in assets and ${result['total_liabilities']:,.2f} in liabilities. "
    response += "Your main accounts are: "
    for acct in result['accounts'][:3]:
        response += f"{acct['name']} with ${abs(acct['balance']):,.2f}, "

    await params.result_callback(response)


async def get_spending_by_category(params: FunctionCallParams):
    """Get spending breakdown by category."""
    logger.info(f"Tool called: get_spending_by_category with {params.arguments}")

    start_date = params.arguments.get("start_date", "this month")

    # TODO: Replace with actual MCP call
    # result = await mcp_client.call_tool("mcp__monarch-money__get_spending_by_category", {
    #     "start_date": start_date
    # })

    # Stub response
    result = {
        "period": start_date,
        "total_spending": 3250.00,
        "categories": [
            {"name": "Groceries", "amount": 650.00},
            {"name": "Restaurants", "amount": 420.00},
            {"name": "Transportation", "amount": 380.00},
            {"name": "Utilities", "amount": 290.00},
            {"name": "Entertainment", "amount": 175.00},
        ]
    }

    response = f"For {result['period']}, you spent ${result['total_spending']:,.2f} total. "
    response += "Top categories: "
    for cat in result['categories'][:3]:
        response += f"{cat['name']} at ${cat['amount']:,.2f}, "

    await params.result_callback(response)


async def search_transactions(params: FunctionCallParams):
    """Search transactions by merchant or category."""
    logger.info(f"Tool called: search_transactions with {params.arguments}")

    query = params.arguments.get("query", "")

    # TODO: Replace with actual MCP call
    # result = await mcp_client.call_tool("mcp__monarch-money__search_transactions", {
    #     "query": query
    # })

    # Stub response
    result = {
        "query": query,
        "count": 5,
        "transactions": [
            {"merchant": "Amazon", "amount": 89.99, "date": "2025-01-25", "category": "Shopping"},
            {"merchant": "Amazon", "amount": 34.50, "date": "2025-01-20", "category": "Shopping"},
            {"merchant": "Amazon", "amount": 156.00, "date": "2025-01-15", "category": "Electronics"},
        ]
    }

    response = f"I found {result['count']} transactions matching '{query}'. "
    response += "Recent ones include: "
    for txn in result['transactions'][:3]:
        response += f"${txn['amount']:.2f} at {txn['merchant']} on {txn['date']}, "

    await params.result_callback(response)


async def get_cluster_status(params: FunctionCallParams):
    """Get Kubernetes cluster health status."""
    logger.info("Tool called: get_cluster_status")

    # TODO: Replace with actual k8s check or MCP call
    # result = await mcp_client.call_tool("mcp__proxmox-k8s__check_health", {})

    # Stub response
    result = {
        "nodes": 3,
        "nodes_ready": 3,
        "pods_running": 42,
        "pods_pending": 0,
        "services": ["argocd", "gitea", "grafana", "prometheus", "homepage"]
    }

    response = f"Your cluster has {result['nodes']} nodes, all healthy. "
    response += f"There are {result['pods_running']} pods running with no pending issues. "
    response += f"Active services include {', '.join(result['services'][:4])} and more."

    await params.result_callback(response)


async def get_current_time(params: FunctionCallParams):
    """Get the current date and time."""
    logger.info("Tool called: get_current_time")
    now = datetime.now()
    response = f"It's currently {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."
    await params.result_callback(response)


# =============================================================================
# TOOL SCHEMAS - Define what the LLM knows about each tool
# =============================================================================

TOOLS = [
    FunctionSchema(
        name="get_account_balances",
        description="Get all account balances and net worth from the user's financial accounts (Monarch Money)",
        properties={},
        required=[],
    ),
    FunctionSchema(
        name="get_spending_by_category",
        description="Get spending breakdown by category for a time period",
        properties={
            "start_date": {
                "type": "string",
                "description": "Start date or period like 'this month', 'last week', '2025-01-01'",
            },
        },
        required=[],
    ),
    FunctionSchema(
        name="search_transactions",
        description="Search transactions by merchant name, category, or description",
        properties={
            "query": {
                "type": "string",
                "description": "Search term like merchant name (Amazon, Starbucks) or category (groceries, restaurants)",
            },
        },
        required=["query"],
    ),
    FunctionSchema(
        name="get_cluster_status",
        description="Get the health status of the Kubernetes homelab cluster including nodes, pods, and services",
        properties={},
        required=[],
    ),
    FunctionSchema(
        name="get_current_time",
        description="Get the current date and time",
        properties={},
        required=[],
    ),
]

# Map function names to implementations
TOOL_HANDLERS = {
    "get_account_balances": get_account_balances,
    "get_spending_by_category": get_spending_by_category,
    "search_transactions": search_transactions,
    "get_cluster_status": get_cluster_status,
    "get_current_time": get_current_time,
}


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are a helpful voice assistant with access to the user's financial data and homelab infrastructure.

You can help with:
- Financial questions: account balances, spending analysis, transaction searches (via Monarch Money)
- Homelab status: Kubernetes cluster health, running services

Keep responses concise and conversational since this is a voice interface.
Avoid long lists - summarize and offer to provide more detail if asked.
Use natural speech patterns and contractions.

When using tools, briefly acknowledge what you're doing, like "Let me check your accounts" or "Looking that up now."

If asked about something you don't have a tool for, be honest about your limitations."""


# =============================================================================
# MAIN BOT SETUP
# =============================================================================

async def main():
    """Main entry point - sets up and runs the voice pipeline."""

    # Validate required environment variables
    required_vars = ["ANTHROPIC_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY", "DAILY_API_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        logger.info("Copy env.example to .env and add your API keys")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        # Create a Daily.co room for the WebRTC connection
        # This gives us a browser-based interface for audio
        room_url = os.getenv("DAILY_ROOM_URL")

        if not room_url:
            # Create a temporary room
            logger.info("Creating temporary Daily room...")
            async with session.post(
                "https://api.daily.co/v1/rooms",
                headers={"Authorization": f"Bearer {os.getenv('DAILY_API_KEY')}"},
                json={
                    "properties": {
                        "exp": int(asyncio.get_event_loop().time()) + 3600,  # 1 hour
                        "enable_chat": False,
                    }
                },
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to create room: {await resp.text()}")
                    sys.exit(1)
                data = await resp.json()
                room_url = data["url"]

        logger.info(f"Room URL: {room_url}")
        logger.info("Open this URL in your browser to talk to the bot!")

        # Daily.co transport handles WebRTC audio streaming
        transport = DailyTransport(
            room_url,
            None,  # No token needed for public rooms
            "Voice Agent",
            DailyParams(
                audio_out_enabled=True,
                audio_out_sample_rate=24000,
                audio_in_enabled=True,
                audio_in_sample_rate=16000,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                transcription_enabled=False,  # We use Deepgram directly
            ),
        )

        # Speech-to-Text: Deepgram
        stt = DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            # Use nova-2 for best accuracy
        )

        # LLM: Claude with tool calling
        llm = AnthropicLLMService(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model="claude-sonnet-4-20250514",
        )

        # Register all tools
        for tool in TOOLS:
            handler = TOOL_HANDLERS.get(tool.name)
            if handler:
                llm.register_function(tool.name, handler)
                logger.info(f"Registered tool: {tool.name}")

        # Text-to-Speech: Cartesia
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",  # British Lady
            # Other voices: "a0e99841-438c-4a64-b679-ae501e7d6091" (Barbershop Man)
        )

        # Conversation context with system prompt and tools
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        context = OpenAILLMContext(messages, TOOLS)
        context_aggregator = llm.create_context_aggregator(context)

        # Build the pipeline
        pipeline = Pipeline(
            [
                transport.input(),           # Audio from browser
                stt,                          # Speech to text
                context_aggregator.user(),    # Add user message to context
                llm,                          # Claude processes and may call tools
                tts,                          # Text to speech
                transport.output(),           # Audio back to browser
                context_aggregator.assistant(),  # Add assistant response to context
            ]
        )

        task = PipelineTask(
            pipeline,
            PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            logger.info(f"Participant joined: {participant['id']}")
            # Greet the user
            await task.queue_frames([
                LLMMessagesFrame([
                    {"role": "user", "content": "Say a brief greeting and ask how you can help."}
                ])
            ])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            logger.info(f"Participant left: {participant['id']}")
            await task.queue_frame(EndFrame())

        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
