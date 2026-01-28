"""Source for importing agent progress data from agent-progress database."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from ..db.source_engine import get_source_session_factory
from .scanner import ConversationFile

logger = logging.getLogger(__name__)

# Maximum content size before truncation (100KB)
MAX_CONTENT_SIZE = 100_000


class AgentProgressSource:
    """Source for importing agent progress data.

    This source reads workflow execution data from the agent-progress
    PostgreSQL database and converts it to ConversationFile format
    for indexing into the conversation-history system.
    """

    def source_type(self) -> str:
        """Return identifier for this source type."""
        return "agent-progress"

    async def scan_all(self) -> list[ConversationFile]:
        """Fetch all workflows and convert to ConversationFile."""
        return await self._fetch_workflows()

    async def scan_project(self, project_name: str) -> list[ConversationFile]:
        """Fetch workflows for a specific project."""
        return await self._fetch_workflows(project_name=project_name)

    async def scan_since(self, since_days: int = 30) -> list[ConversationFile]:
        """Fetch workflows from the last N days.

        Args:
            since_days: Number of days to look back (default: 30)

        Returns:
            List of ConversationFile objects for recent workflows.
        """
        since_date = datetime.now(timezone.utc) - timedelta(days=since_days)
        return await self._fetch_workflows(since_date=since_date)

    async def scan_workflow(self, workflow_id: str) -> list[ConversationFile]:
        """Fetch a specific workflow by ID.

        Args:
            workflow_id: UUID of the workflow to fetch.

        Returns:
            List with single ConversationFile or empty if not found.
        """
        return await self._fetch_workflows(workflow_id=workflow_id)

    async def _fetch_workflows(
        self,
        project_name: str | None = None,
        since_date: datetime | None = None,
        workflow_id: str | None = None,
    ) -> list[ConversationFile]:
        """Fetch workflows from agent-progress database.

        Args:
            project_name: Filter by project name (optional).
            since_date: Only fetch workflows started after this date.
            workflow_id: Fetch a specific workflow by ID.

        Returns:
            List of ConversationFile objects.
        """
        try:
            session_factory = get_source_session_factory()
        except ValueError as e:
            logger.error(f"Source database not configured: {e}")
            return []

        results = []

        async with session_factory() as session:
            try:
                # Build workflow query
                workflow_query = """
                    SELECT
                        w.id,
                        w.name,
                        w.project_name,
                        w.status,
                        w.started_at,
                        w.completed_at,
                        w.metadata,
                        w.created_at
                    FROM workflows w
                    WHERE 1=1
                """
                params: dict[str, Any] = {}

                if workflow_id:
                    workflow_query += " AND w.id = :workflow_id"
                    params["workflow_id"] = workflow_id
                if project_name:
                    workflow_query += " AND w.project_name = :project_name"
                    params["project_name"] = project_name
                if since_date:
                    workflow_query += " AND w.started_at >= :since_date"
                    params["since_date"] = since_date

                workflow_query += " ORDER BY w.started_at DESC"

                workflow_result = await session.execute(
                    text(workflow_query), params
                )
                workflows = workflow_result.fetchall()

                for workflow in workflows:
                    try:
                        # Fetch agents for this workflow
                        agents = await self._fetch_agents(session, str(workflow.id))

                        # Fetch events for each agent
                        agent_events = {}
                        for agent in agents:
                            events = await self._fetch_events(
                                session, str(agent.id)
                            )
                            agent_events[str(agent.id)] = events

                        # Convert to ConversationFile
                        conv_file = self._workflow_to_conversation(
                            workflow, agents, agent_events
                        )
                        if conv_file:
                            results.append(conv_file)

                    except Exception as e:
                        logger.error(
                            f"Error processing workflow {workflow.id}: {e}"
                        )
                        continue

            except Exception as e:
                logger.error(f"Error fetching workflows: {e}")

        return results

    async def _fetch_agents(self, session, workflow_id: str) -> list:
        """Fetch all agents for a workflow."""
        query = """
            SELECT
                a.id,
                a.name,
                a.agent_type,
                a.status,
                a.progress,
                a.started_at,
                a.completed_at,
                a.parent_id,
                a.metadata
            FROM agents a
            WHERE a.workflow_id = :workflow_id
            ORDER BY a.started_at ASC
        """
        result = await session.execute(text(query), {"workflow_id": workflow_id})
        return result.fetchall()

    async def _fetch_events(self, session, agent_id: str) -> list:
        """Fetch all events for an agent."""
        query = """
            SELECT
                e.id,
                e.event_type,
                e.payload,
                e.created_at
            FROM agent_events e
            WHERE e.agent_id = :agent_id
            ORDER BY e.created_at ASC
        """
        result = await session.execute(text(query), {"agent_id": agent_id})
        return result.fetchall()

    def _workflow_to_conversation(
        self,
        workflow,
        agents: list,
        agent_events: dict[str, list],
    ) -> ConversationFile | None:
        """Transform workflow data into a ConversationFile.

        Args:
            workflow: Workflow row from database.
            agents: List of agent rows.
            agent_events: Dict mapping agent_id to list of events.

        Returns:
            ConversationFile or None if content is empty.
        """
        # Build markdown document optimized for embedding search
        lines = []

        # Header
        workflow_name = workflow.name or "Unnamed Workflow"
        lines.append(f"# {workflow_name} - Agent Workflow Execution")
        lines.append("")

        # Metadata
        project = workflow.project_name or "unknown"
        lines.append(f"Project: {project}")
        lines.append(f"Status: {workflow.status or 'unknown'}")

        if workflow.started_at:
            started = workflow.started_at.isoformat()
            completed = (
                workflow.completed_at.isoformat()
                if workflow.completed_at
                else "in progress"
            )
            lines.append(f"Duration: {started} to {completed}")

        # Agent names summary
        agent_names = [a.name or a.agent_type for a in agents]
        if agent_names:
            lines.append(f"Agents: {', '.join(agent_names)}")

        lines.append("")

        # Summary section
        lines.append("## Summary")
        task_summaries = self._extract_task_summaries(agents, agent_events)
        if task_summaries:
            lines.append(
                f"This workflow executed {len(agents)} agents. "
                f"The main tasks included: {task_summaries}"
            )
        else:
            lines.append(f"This workflow executed {len(agents)} agents.")
        lines.append("")

        # Agent hierarchy
        if agents:
            lines.append("## Agent Hierarchy")
            lines.append("")

            for agent in agents:
                agent_name = agent.name or "unnamed"
                agent_type = agent.agent_type or "unknown"
                lines.append(f"### {agent_name} ({agent_type})")

                status = agent.status or "unknown"
                progress = agent.progress or 0
                lines.append(f"Status: {status} | Progress: {progress}%")

                if agent.started_at:
                    started = agent.started_at.isoformat()
                    completed = (
                        agent.completed_at.isoformat()
                        if agent.completed_at
                        else "in progress"
                    )
                    lines.append(f"Started: {started} | Completed: {completed}")

                lines.append("")

                # Events for this agent
                events = agent_events.get(str(agent.id), [])
                if events:
                    lines.append("#### Event Timeline")
                    for event in events[:50]:  # Limit events per agent
                        timestamp = (
                            event.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            if event.created_at
                            else "unknown"
                        )
                        event_type = event.event_type or "event"
                        payload_summary = self._summarize_payload(event.payload)
                        lines.append(f"- {timestamp}: {event_type} - {payload_summary}")
                    lines.append("")

        content = "\n".join(lines)

        # Truncate if too large
        if len(content) > MAX_CONTENT_SIZE:
            content = content[:MAX_CONTENT_SIZE]
            content += "\n\n[Content truncated due to size]"

        # Remove null bytes
        content = content.replace("\x00", "")

        if not content.strip():
            return None

        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Generate source_id for deduplication
        source_id = f"agent-progress:workflow:{workflow.id}"

        # Determine doc_type (agent-execution is a new type for this source)
        doc_type = "agent-execution"

        return ConversationFile(
            file_path=source_id,  # Use source_id as file_path for uniqueness
            project_name=workflow.project_name or "agent-progress",
            feature_name=workflow.name,
            doc_type=doc_type,
            title=f"{workflow_name} - {workflow.status or 'unknown'}",
            content=content,
            content_hash=content_hash,
        )

    def _extract_task_summaries(
        self, agents: list, agent_events: dict[str, list]
    ) -> str:
        """Extract task summary from agent events.

        Looks for meaningful events like tool calls, completions, etc.
        """
        summaries = []
        for agent in agents[:5]:  # Limit to first 5 agents
            events = agent_events.get(str(agent.id), [])
            for event in events:
                if event.event_type in ("task_complete", "tool_result", "completion"):
                    payload = event.payload or {}
                    if isinstance(payload, dict):
                        summary = payload.get("summary") or payload.get("message", "")
                        if summary and len(summary) < 100:
                            summaries.append(summary)
                            break

        return "; ".join(summaries[:3]) if summaries else ""

    def _summarize_payload(self, payload) -> str:
        """Create a brief summary of an event payload."""
        if not payload:
            return "(no details)"

        if isinstance(payload, dict):
            # Try common fields
            for key in ("message", "summary", "status", "result", "error"):
                if key in payload:
                    value = str(payload[key])[:100]
                    return value

            # Fall back to key names
            keys = list(payload.keys())[:3]
            return f"({', '.join(keys)})"

        if isinstance(payload, str):
            return payload[:100]

        return str(payload)[:100]
