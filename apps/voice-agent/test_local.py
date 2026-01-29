"""
Local voice agent - uses OpenAI for STT/TTS and Anthropic for LLM.
Only needs ANTHROPIC_API_KEY and OPENAI_API_KEY.

Run with: uv run test_local.py
Press Ctrl+C to exit.
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.anthropic.llm import AnthropicLLMService
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="INFO")


# =============================================================================
# STUB TOOLS
# =============================================================================

async def get_account_balances(params: FunctionCallParams):
    """Get all account balances."""
    logger.info("Tool: get_account_balances")
    response = "Your net worth is $110,000. Checking has $5,200, savings has $25,000, investments have $94,800."
    await params.result_callback(response)


async def get_spending_by_category(params: FunctionCallParams):
    """Get spending by category."""
    logger.info(f"Tool: get_spending_by_category({params.arguments})")
    response = "This month you spent $3,250 total. Top categories: Groceries $650, Restaurants $420, Transportation $380."
    await params.result_callback(response)


async def search_transactions(params: FunctionCallParams):
    """Search transactions."""
    query = params.arguments.get("query", "")
    logger.info(f"Tool: search_transactions({query})")
    response = f"Found 5 transactions for '{query}'. Recent ones: $89.99 on January 25th, $34.50 on January 20th."
    await params.result_callback(response)


async def get_cluster_status(params: FunctionCallParams):
    """Get K8s cluster status."""
    logger.info("Tool: get_cluster_status")
    response = "Your cluster has 3 nodes, all healthy. 42 pods running with no issues. Services include ArgoCD, Gitea, Grafana, and Prometheus."
    await params.result_callback(response)


async def get_current_time(params: FunctionCallParams):
    """Get current time."""
    now = datetime.now()
    response = f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}."
    await params.result_callback(response)


TOOLS = [
    FunctionSchema(name="get_account_balances", description="Get financial account balances and net worth", properties={}, required=[]),
    FunctionSchema(name="get_spending_by_category", description="Get spending breakdown by category", properties={"start_date": {"type": "string", "description": "Time period"}}, required=[]),
    FunctionSchema(name="search_transactions", description="Search transactions by merchant", properties={"query": {"type": "string", "description": "Search term"}}, required=["query"]),
    FunctionSchema(name="get_cluster_status", description="Get Kubernetes cluster health", properties={}, required=[]),
    FunctionSchema(name="get_current_time", description="Get current date and time", properties={}, required=[]),
]

TOOL_HANDLERS = {
    "get_account_balances": get_account_balances,
    "get_spending_by_category": get_spending_by_category,
    "search_transactions": search_transactions,
    "get_cluster_status": get_cluster_status,
    "get_current_time": get_current_time,
}

SYSTEM_PROMPT = """You are a helpful voice assistant. Keep responses brief and conversational - just 1-2 sentences.
You can check financial accounts, search transactions, and check cluster status.
When using a tool, just say something brief like "Let me check" before the result."""


async def main():
    """Run voice agent with local audio."""

    # Check API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key:
        logger.error("Missing ANTHROPIC_API_KEY")
        sys.exit(1)
    if not openai_key:
        logger.error("Missing OPENAI_API_KEY")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("Starting voice agent...")
    logger.info("Speak into your microphone. Press Ctrl+C to exit.")
    logger.info("=" * 50)

    # Local audio transport (uses system mic/speakers)
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_out_enabled=True,
            audio_in_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        )
    )

    # STT: OpenAI Whisper
    stt = OpenAISTTService(
        api_key=openai_key,
        model="whisper-1",
    )

    # LLM: Anthropic Claude with tools
    llm = AnthropicLLMService(
        api_key=anthropic_key,
        model="claude-sonnet-4-20250514",
    )
    for tool in TOOLS:
        llm.register_function(tool.name, TOOL_HANDLERS[tool.name])
        logger.info(f"Registered tool: {tool.name}")

    # TTS: OpenAI
    tts = OpenAITTSService(
        api_key=openai_key,
        voice="nova",  # Options: alloy, echo, fable, onyx, nova, shimmer
    )

    # Context with tools
    tools_schema = ToolsSchema(standard_tools=TOOLS)
    context = OpenAILLMContext([{"role": "system", "content": SYSTEM_PROMPT}], tools_schema)
    context_aggregator = llm.create_context_aggregator(context)

    # Pipeline
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

    runner = PipelineRunner()

    try:
        await runner.run(task)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
