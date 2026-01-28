"""Sync tools for indexing conversations."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, select

from ...db.models import Conversation, IndexStatus


def register_sync_tools(mcp: FastMCP, get_session):
    """Register sync tools with the MCP server."""

    @mcp.tool()
    async def trigger_index(
        project: str | None = None,
        force: bool = False,
    ) -> dict:
        """Trigger indexing of conversation files.

        Args:
            project: Index only this project (optional, indexes all if not specified)
            force: Force re-indexing even if content hasn't changed (default False)
        """
        from ...config import settings
        from ...indexer import ConversationIndexer, ConversationScanner

        if not settings.has_openai:
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "help": "Set OPENAI_API_KEY environment variable.",
            }

        try:
            scanner = ConversationScanner(settings.projects_root)

            async with get_session() as session:
                indexer = ConversationIndexer(session, scanner=scanner)

                if project:
                    result = await indexer.index_project(project, force=force)
                else:
                    result = await indexer.index_all(force=force)

                return {
                    "success": result.files_failed == 0,
                    "project": project,
                    "force": force,
                    "files_indexed": result.files_indexed,
                    "files_updated": result.files_updated,
                    "files_skipped": result.files_skipped,
                    "files_failed": result.files_failed,
                    "errors": result.errors[:5] if result.errors else [],
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def get_index_status() -> dict:
        """Get current indexing statistics and status."""
        async with get_session() as session:
            # Get overall counts
            total_stmt = select(func.count(Conversation.id))
            total_result = await session.execute(total_stmt)
            total_count = total_result.scalar() or 0

            embedded_stmt = select(func.count(Conversation.id)).where(
                Conversation.embedding.isnot(None)
            )
            embedded_result = await session.execute(embedded_stmt)
            embedded_count = embedded_result.scalar() or 0

            # Get per-project counts
            project_stmt = (
                select(
                    Conversation.project_name,
                    func.count(Conversation.id).label("count"),
                )
                .group_by(Conversation.project_name)
                .order_by(func.count(Conversation.id).desc())
            )
            project_result = await session.execute(project_stmt)
            projects = [
                {"project": row.project_name, "count": row.count}
                for row in project_result.all()
            ]

            # Get doc type counts
            doctype_stmt = (
                select(
                    Conversation.doc_type,
                    func.count(Conversation.id).label("count"),
                )
                .group_by(Conversation.doc_type)
            )
            doctype_result = await session.execute(doctype_stmt)
            doc_types = {row.doc_type: row.count for row in doctype_result.all()}

            # Get last index status
            status_stmt = (
                select(IndexStatus)
                .where(IndexStatus.project_name.is_(None))
                .order_by(IndexStatus.last_index_at.desc())
                .limit(1)
            )
            status_result = await session.execute(status_stmt)
            last_status = status_result.scalar_one_or_none()

            return {
                "total_conversations": total_count,
                "with_embeddings": embedded_count,
                "projects": projects,
                "doc_types": doc_types,
                "last_index": {
                    "status": last_status.status if last_status else "never",
                    "at": (
                        last_status.last_index_at.isoformat()
                        if last_status and last_status.last_index_at
                        else None
                    ),
                    "files_indexed": last_status.files_indexed if last_status else 0,
                    "files_updated": last_status.files_updated if last_status else 0,
                    "files_failed": last_status.files_failed if last_status else 0,
                    "error": last_status.error_message if last_status else None,
                },
            }

    @mcp.tool()
    async def delete_project_index(project: str) -> dict:
        """Delete all indexed conversations for a project.

        Args:
            project: Project name to delete from index
        """
        from sqlalchemy import delete

        async with get_session() as session:
            # Count before delete
            count_stmt = select(func.count(Conversation.id)).where(
                Conversation.project_name == project
            )
            count_result = await session.execute(count_stmt)
            count = count_result.scalar() or 0

            if count == 0:
                return {
                    "success": True,
                    "project": project,
                    "deleted": 0,
                    "message": "No conversations found for this project.",
                }

            # Delete conversations (chunks cascade delete)
            delete_stmt = delete(Conversation).where(
                Conversation.project_name == project
            )
            await session.execute(delete_stmt)
            await session.commit()

            return {
                "success": True,
                "project": project,
                "deleted": count,
            }

    @mcp.tool()
    async def import_agent_progress(
        workflow_id: str | None = None,
        since_days: int = 30,
        force: bool = False,
        dry_run: bool = False,
    ) -> dict:
        """Import agent progress data into conversation history.

        Imports workflow execution data from the agent-progress PostgreSQL
        database, making it searchable via semantic and keyword search.

        Args:
            workflow_id: Import specific workflow by ID (optional)
            since_days: Import workflows from last N days (default: 30)
            force: Re-import even if already indexed (default: False)
            dry_run: Preview what would be imported without changes (default: False)

        Returns:
            Import statistics including workflows_found, workflows_imported, etc.
        """
        from ...config import settings
        from ...indexer import AgentProgressSource, ConversationIndexer

        # Check prerequisites
        if not settings.has_source_database:
            return {
                "success": False,
                "error": "Source database not configured",
                "help": "Set SOURCE_DATABASE_URL or SOURCE_DATABASE_PASSWORD environment variable.",
            }

        if not settings.has_openai and not dry_run:
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "help": "Set OPENAI_API_KEY environment variable for embeddings.",
            }

        try:
            source = AgentProgressSource()

            # Fetch workflows based on criteria
            if workflow_id:
                files = await source.scan_workflow(workflow_id)
            else:
                files = await source.scan_since(since_days)

            if dry_run:
                # Return preview without indexing
                return {
                    "success": True,
                    "dry_run": True,
                    "workflows_found": len(files),
                    "workflows": [
                        {
                            "source_id": f.file_path,
                            "project": f.project_name,
                            "title": f.title,
                            "doc_type": f.doc_type,
                            "content_length": len(f.content),
                        }
                        for f in files[:20]  # Limit preview
                    ],
                    "message": f"Found {len(files)} workflows to import. Run without dry_run to import.",
                }

            # Index the files
            async with get_session() as session:
                indexer = ConversationIndexer(session, source=source)
                result = await indexer.index_files(files, force=force)

                return {
                    "success": result.files_failed == 0,
                    "dry_run": False,
                    "workflows_found": len(files),
                    "workflows_indexed": result.files_indexed,
                    "workflows_updated": result.files_updated,
                    "workflows_skipped": result.files_skipped,
                    "workflows_failed": result.files_failed,
                    "errors": result.errors[:5] if result.errors else [],
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
