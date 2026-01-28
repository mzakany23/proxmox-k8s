"""Browse tools for listing and retrieving conversations."""

from datetime import datetime, timedelta, timezone

from mcp.server.fastmcp import FastMCP
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import selectinload

from ...db.models import Conversation


def register_browse_tools(mcp: FastMCP, get_session):
    """Register browse tools with the MCP server."""

    @mcp.tool()
    async def list_projects() -> dict:
        """List all indexed projects with conversation counts."""
        async with get_session() as session:
            stmt = (
                select(
                    Conversation.project_name,
                    func.count(Conversation.id).label("count"),
                )
                .group_by(Conversation.project_name)
                .order_by(func.count(Conversation.id).desc())
            )

            result = await session.execute(stmt)
            rows = result.all()

            projects = []
            total_count = 0
            for row in rows:
                projects.append({
                    "project_name": row.project_name,
                    "conversation_count": row.count,
                })
                total_count += row.count

            return {
                "total_projects": len(projects),
                "total_conversations": total_count,
                "projects": projects,
            }

    @mcp.tool()
    async def list_features(project: str) -> dict:
        """List features/topics within a project.

        Args:
            project: Project name to list features for
        """
        async with get_session() as session:
            stmt = (
                select(
                    Conversation.feature_name,
                    func.count(Conversation.id).label("count"),
                )
                .where(Conversation.project_name == project)
                .group_by(Conversation.feature_name)
                .order_by(func.count(Conversation.id).desc())
            )

            result = await session.execute(stmt)
            rows = result.all()

            features = []
            for row in rows:
                features.append({
                    "feature_name": row.feature_name or "(root)",
                    "conversation_count": row.count,
                })

            return {
                "project": project,
                "total_features": len(features),
                "features": features,
            }

    @mcp.tool()
    async def list_checkpoints(
        project: str | None = None,
        days: int = 30,
    ) -> dict:
        """List recent checkpoint conversations.

        Args:
            project: Filter by project name (optional)
            days: Number of days to look back (default 30)
        """
        async with get_session() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            stmt = (
                select(
                    Conversation.file_path,
                    Conversation.project_name,
                    Conversation.feature_name,
                    Conversation.title,
                    Conversation.indexed_at,
                )
                .where(Conversation.doc_type == "checkpoint")
                .where(Conversation.indexed_at >= cutoff)
                .order_by(Conversation.indexed_at.desc())
            )

            if project:
                stmt = stmt.where(Conversation.project_name == project)

            result = await session.execute(stmt)
            rows = result.all()

            checkpoints = []
            for row in rows:
                checkpoints.append({
                    "file_path": row.file_path,
                    "project_name": row.project_name,
                    "feature_name": row.feature_name,
                    "title": row.title,
                    "indexed_at": row.indexed_at.isoformat() if row.indexed_at else None,
                })

            return {
                "days": days,
                "project": project,
                "count": len(checkpoints),
                "checkpoints": checkpoints,
            }

    @mcp.tool()
    async def get_conversation(file_path: str) -> dict:
        """Get full content and metadata for a conversation.

        Args:
            file_path: Path to the conversation file
        """
        async with get_session() as session:
            stmt = (
                select(Conversation)
                .options(selectinload(Conversation.chunks))
                .where(Conversation.file_path == file_path)
            )
            result = await session.execute(stmt)
            conv = result.scalar_one_or_none()

            if not conv:
                return {
                    "error": f"Conversation not found: {file_path}",
                    "help": "Run trigger_index() to index conversations.",
                }

            return {
                "file_path": conv.file_path,
                "project_name": conv.project_name,
                "feature_name": conv.feature_name,
                "doc_type": conv.doc_type,
                "title": conv.title,
                "content": conv.content,
                "indexed_at": conv.indexed_at.isoformat() if conv.indexed_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "has_embedding": conv.embedding is not None,
                "chunk_count": len(conv.chunks) if conv.chunks else 0,
            }

    @mcp.tool()
    async def list_by_type(
        doc_type: str,
        project: str | None = None,
        limit: int = 20,
    ) -> dict:
        """List conversations by document type.

        Args:
            doc_type: Document type to filter by (checkpoint, instructions, docs, other)
            project: Filter by project name (optional)
            limit: Maximum results to return (default 20)
        """
        async with get_session() as session:
            stmt = (
                select(
                    Conversation.file_path,
                    Conversation.project_name,
                    Conversation.feature_name,
                    Conversation.title,
                    Conversation.indexed_at,
                )
                .where(Conversation.doc_type == doc_type)
                .order_by(Conversation.indexed_at.desc())
                .limit(limit)
            )

            if project:
                stmt = stmt.where(Conversation.project_name == project)

            result = await session.execute(stmt)
            rows = result.all()

            conversations = []
            for row in rows:
                conversations.append({
                    "file_path": row.file_path,
                    "project_name": row.project_name,
                    "feature_name": row.feature_name,
                    "title": row.title,
                    "indexed_at": row.indexed_at.isoformat() if row.indexed_at else None,
                })

            return {
                "doc_type": doc_type,
                "project": project,
                "count": len(conversations),
                "conversations": conversations,
            }
