"""CLI entry points for conversation history."""

import asyncio
import sys


def index_main():
    """CLI entry point for indexing conversations."""
    import argparse

    parser = argparse.ArgumentParser(description="Index conversation files")
    parser.add_argument(
        "--project",
        "-p",
        help="Index only this project",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-indexing even if content unchanged",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database tables",
    )
    parser.add_argument(
        "--import-agent-progress",
        action="store_true",
        help="Import workflows from agent-progress database",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=30,
        help="For agent-progress import: number of days to look back (default: 30)",
    )
    parser.add_argument(
        "--workflow-id",
        help="For agent-progress import: specific workflow UUID to import",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be imported without making changes",
    )
    args = parser.parse_args()

    if args.import_agent_progress:
        asyncio.run(
            _run_agent_progress_import(
                args.workflow_id,
                args.since_days,
                args.force,
                args.dry_run,
            )
        )
    else:
        asyncio.run(_run_index(args.project, args.force, args.init_db))


async def _run_index(project: str | None, force: bool, init_db: bool):
    """Run the indexing process."""
    from sqlalchemy import text

    from .config import settings
    from .db import AsyncSessionLocal
    from .db.engine import engine
    from .db.models import Base
    from .indexer import ConversationIndexer, ConversationScanner

    if init_db:
        print("Initializing database tables...")
        async with engine.begin() as conn:
            # Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        print("Database initialized.")

    if not settings.has_openai:
        print("ERROR: OPENAI_API_KEY not configured", file=sys.stderr)
        sys.exit(1)

    scanner = ConversationScanner(settings.projects_root)

    async with AsyncSessionLocal() as session:
        indexer = ConversationIndexer(session, scanner=scanner)

        if project:
            print(f"Indexing project: {project}")
            result = await indexer.index_project(project, force=force)
        else:
            print("Indexing all projects...")
            result = await indexer.index_all(force=force)

        print(f"\nIndexing complete:")
        print(f"  New files indexed: {result.files_indexed}")
        print(f"  Files updated: {result.files_updated}")
        print(f"  Files skipped: {result.files_skipped}")
        print(f"  Files failed: {result.files_failed}")

        if result.errors:
            print(f"\nErrors:")
            for error in result.errors[:10]:
                print(f"  - {error}")


async def _run_agent_progress_import(
    workflow_id: str | None,
    since_days: int,
    force: bool,
    dry_run: bool,
):
    """Run the agent-progress import process."""
    from .config import settings
    from .db import AsyncSessionLocal
    from .indexer import AgentProgressSource, ConversationIndexer

    if not settings.has_source_database:
        print(
            "ERROR: Source database not configured. "
            "Set SOURCE_DATABASE_URL or SOURCE_DATABASE_PASSWORD.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not settings.has_openai and not dry_run:
        print("ERROR: OPENAI_API_KEY not configured", file=sys.stderr)
        sys.exit(1)

    source = AgentProgressSource()

    # Fetch workflows based on criteria
    print("Scanning agent-progress database...")
    if workflow_id:
        print(f"  Looking for workflow: {workflow_id}")
        files = await source.scan_workflow(workflow_id)
    else:
        print(f"  Looking for workflows from last {since_days} days")
        files = await source.scan_since(since_days)

    print(f"Found {len(files)} workflows")

    if dry_run:
        print("\nDry run - would import:")
        for f in files[:20]:
            print(f"  - {f.title} ({f.project_name}) [{len(f.content)} chars]")
        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more")
        return

    if not files:
        print("No workflows to import.")
        return

    async with AsyncSessionLocal() as session:
        indexer = ConversationIndexer(session, source=source)
        result = await indexer.index_files(files, force=force)

        print(f"\nImport complete:")
        print(f"  Workflows indexed: {result.files_indexed}")
        print(f"  Workflows updated: {result.files_updated}")
        print(f"  Workflows skipped: {result.files_skipped}")
        print(f"  Workflows failed: {result.files_failed}")

        if result.errors:
            print(f"\nErrors:")
            for error in result.errors[:10]:
                print(f"  - {error}")


if __name__ == "__main__":
    index_main()
