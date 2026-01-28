"""Main indexer orchestrator."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import or_

from ..db.models import Conversation, ConversationChunk, IndexStatus
from .embedder import Embedder
from .scanner import ConversationFile, ConversationScanner, chunk_content
from .source import ConversationSource

logger = logging.getLogger(__name__)


@dataclass
class IndexResult:
    """Result of an indexing operation."""

    files_indexed: int
    files_updated: int
    files_skipped: int
    files_failed: int
    errors: list[str]


class ConversationIndexer:
    """Orchestrates the indexing of conversation files."""

    def __init__(
        self,
        session: AsyncSession,
        source: ConversationSource | ConversationScanner | None = None,
        embedder: Embedder | None = None,
        # Deprecated: use 'source' instead
        scanner: ConversationScanner | None = None,
    ):
        self.session = session
        # Support both 'source' and deprecated 'scanner' parameter
        self.source = source or scanner or ConversationScanner()
        self.embedder = embedder or Embedder()

    async def index_all(self, force: bool = False) -> IndexResult:
        """Index all conversations across all projects."""
        files = await self.source.scan_all()
        return await self._index_files(files, force=force)

    async def index_project(self, project_name: str, force: bool = False) -> IndexResult:
        """Index conversations for a specific project."""
        files = await self.source.scan_project(project_name)
        return await self._index_files(files, force=force, project_name=project_name)

    async def index_files(
        self, files: list[ConversationFile], force: bool = False
    ) -> IndexResult:
        """Index a specific list of conversation files.

        This is useful for importing data from external sources where
        you already have the files prepared.
        """
        return await self._index_files(files, force=force)

    async def _index_files(
        self,
        files: list[ConversationFile],
        force: bool = False,
        project_name: str | None = None,
    ) -> IndexResult:
        """Index a list of conversation files."""
        result = IndexResult(
            files_indexed=0,
            files_updated=0,
            files_skipped=0,
            files_failed=0,
            errors=[],
        )

        # Update status to indexing
        await self._update_status(project_name, "indexing")

        for file in files:
            try:
                indexed = await self._index_file(file, force=force)
                if indexed == "new":
                    result.files_indexed += 1
                    # Commit after each successful index to avoid losing work
                    await self.session.commit()
                elif indexed == "updated":
                    result.files_updated += 1
                    await self.session.commit()
                else:
                    result.files_skipped += 1
            except Exception as e:
                result.files_failed += 1
                error_msg = f"Failed to index {file.file_path}: {e}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                # Rollback failed transaction so we can continue
                await self.session.rollback()

        # Update final status
        await self._update_status(
            project_name,
            "success" if result.files_failed == 0 else "partial",
            result,
        )

        return result

    async def _index_file(
        self, file: ConversationFile, force: bool = False
    ) -> str:
        """Index a single conversation file. Returns 'new', 'updated', or 'skipped'."""
        # Determine source_id - for agent-progress sources, file_path is the source_id
        source_id = None
        if file.file_path.startswith("agent-progress:"):
            source_id = file.file_path

        # Check if file already exists by file_path or source_id
        if source_id:
            # For external sources, prefer source_id for deduplication
            existing = await self.session.execute(
                select(Conversation).where(
                    or_(
                        Conversation.source_id == source_id,
                        Conversation.file_path == file.file_path,
                    )
                )
            )
        else:
            existing = await self.session.execute(
                select(Conversation).where(Conversation.file_path == file.file_path)
            )
        existing_conv = existing.scalar_one_or_none()

        if existing_conv:
            # Check if content changed
            if not force and existing_conv.content_hash == file.content_hash:
                return "skipped"

            # Update existing conversation
            await self._update_conversation(existing_conv, file, source_id)
            return "updated"
        else:
            # Create new conversation
            await self._create_conversation(file, source_id)
            return "new"

    async def _create_conversation(
        self, file: ConversationFile, source_id: str | None = None
    ) -> Conversation:
        """Create a new conversation with chunks and embeddings."""
        # Generate embedding for full content (truncated if needed)
        content_for_embedding = file.content[:8000]  # OpenAI limit
        embedding = await self.embedder.embed_text(content_for_embedding)

        conv = Conversation(
            file_path=file.file_path,
            project_name=file.project_name,
            feature_name=file.feature_name,
            doc_type=file.doc_type,
            title=file.title,
            content=file.content,
            content_hash=file.content_hash,
            source_id=source_id,
            embedding=embedding,
        )
        self.session.add(conv)
        await self.session.flush()  # Get the ID

        # Create chunks
        await self._create_chunks(conv, file.content)

        return conv

    async def _update_conversation(
        self, conv: Conversation, file: ConversationFile, source_id: str | None = None
    ) -> None:
        """Update an existing conversation."""
        # Update metadata
        conv.project_name = file.project_name
        conv.feature_name = file.feature_name
        conv.doc_type = file.doc_type
        conv.title = file.title
        conv.content = file.content
        conv.content_hash = file.content_hash
        conv.updated_at = datetime.now(timezone.utc)
        if source_id:
            conv.source_id = source_id

        # Regenerate embedding
        content_for_embedding = file.content[:8000]
        conv.embedding = await self.embedder.embed_text(content_for_embedding)

        # Delete old chunks and recreate
        for chunk in conv.chunks:
            await self.session.delete(chunk)
        await self.session.flush()

        await self._create_chunks(conv, file.content)

    async def _create_chunks(self, conv: Conversation, content: str) -> None:
        """Create chunks for a conversation."""
        chunks = chunk_content(content)

        if len(chunks) <= 1:
            # No need for chunks if content fits in one
            return

        # Generate embeddings for all chunks
        embeddings = await self.embedder.embed_batch(chunks)

        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = ConversationChunk(
                conversation_id=conv.id,
                chunk_index=i,
                content=chunk_text,
                embedding=embedding,
            )
            self.session.add(chunk)

    async def _update_status(
        self,
        project_name: str | None,
        status: str,
        result: IndexResult | None = None,
    ) -> None:
        """Update indexing status."""
        # Find or create status record
        query = select(IndexStatus)
        if project_name:
            query = query.where(IndexStatus.project_name == project_name)
        else:
            query = query.where(IndexStatus.project_name.is_(None))

        existing = await self.session.execute(query)
        status_record = existing.scalar_one_or_none()

        if not status_record:
            status_record = IndexStatus(project_name=project_name)
            self.session.add(status_record)

        status_record.status = status
        status_record.last_index_at = datetime.now(timezone.utc)

        if result:
            status_record.files_indexed = result.files_indexed
            status_record.files_updated = result.files_updated
            status_record.files_failed = result.files_failed
            if result.errors:
                status_record.error_message = "\n".join(result.errors[:5])

        await self.session.commit()
