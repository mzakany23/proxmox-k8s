"""Search tools for conversation history."""

from mcp.server.fastmcp import FastMCP
from pgvector.sqlalchemy import Vector
from sqlalchemy import func, select, or_, text

from ...db.models import Conversation, ConversationChunk


def register_search_tools(mcp: FastMCP, get_session):
    """Register search tools with the MCP server."""

    @mcp.tool()
    async def search_conversations(
        query: str,
        project: str | None = None,
        doc_type: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Semantic search across all conversations.

        Args:
            query: Search query text
            project: Filter by project name (optional)
            doc_type: Filter by document type: checkpoint, instructions, docs, other (optional)
            limit: Maximum results to return (default 10)
        """
        from ...indexer.embedder import Embedder

        try:
            # Generate embedding for query
            embedder = Embedder()
            query_embedding = await embedder.embed_text(query)

            async with get_session() as session:
                # Build vector similarity search query
                # Using cosine distance (1 - cosine_similarity)
                distance = Conversation.embedding.cosine_distance(query_embedding)

                stmt = (
                    select(
                        Conversation.id,
                        Conversation.file_path,
                        Conversation.project_name,
                        Conversation.feature_name,
                        Conversation.doc_type,
                        Conversation.title,
                        distance.label("distance"),
                    )
                    .where(Conversation.embedding.isnot(None))
                    .order_by(distance)
                    .limit(limit)
                )

                # Apply filters
                if project:
                    stmt = stmt.where(Conversation.project_name == project)
                if doc_type:
                    stmt = stmt.where(Conversation.doc_type == doc_type)

                result = await session.execute(stmt)
                rows = result.all()

                results = []
                for row in rows:
                    # Convert distance to similarity score (0-1, higher is better)
                    similarity = 1 - row.distance

                    results.append({
                        "file_path": row.file_path,
                        "project_name": row.project_name,
                        "feature_name": row.feature_name,
                        "doc_type": row.doc_type,
                        "title": row.title,
                        "similarity": round(similarity, 4),
                    })

                return {
                    "query": query,
                    "count": len(results),
                    "results": results,
                }

        except Exception as e:
            return {
                "error": str(e),
                "help": "Ensure OpenAI API key is configured and database is running.",
            }

    @mcp.tool()
    async def find_similar(
        file_path: str,
        limit: int = 5,
    ) -> dict:
        """Find documents similar to a reference file.

        Args:
            file_path: Path to the reference conversation file
            limit: Maximum results to return (default 5)
        """
        async with get_session() as session:
            # Get the reference document
            stmt = select(Conversation).where(Conversation.file_path == file_path)
            result = await session.execute(stmt)
            reference = result.scalar_one_or_none()

            if not reference:
                return {
                    "error": f"File not found in index: {file_path}",
                    "help": "Run trigger_index() to index the file first.",
                }

            if reference.embedding is None:
                return {
                    "error": "Reference file has no embedding.",
                    "help": "Run trigger_index(force=True) to regenerate embeddings.",
                }

            # Find similar documents
            distance = Conversation.embedding.cosine_distance(reference.embedding)

            stmt = (
                select(
                    Conversation.file_path,
                    Conversation.project_name,
                    Conversation.feature_name,
                    Conversation.doc_type,
                    Conversation.title,
                    distance.label("distance"),
                )
                .where(Conversation.embedding.isnot(None))
                .where(Conversation.file_path != file_path)  # Exclude reference
                .order_by(distance)
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.all()

            results = []
            for row in rows:
                similarity = 1 - row.distance
                results.append({
                    "file_path": row.file_path,
                    "project_name": row.project_name,
                    "feature_name": row.feature_name,
                    "doc_type": row.doc_type,
                    "title": row.title,
                    "similarity": round(similarity, 4),
                })

            return {
                "reference": {
                    "file_path": reference.file_path,
                    "title": reference.title,
                },
                "count": len(results),
                "results": results,
            }

    @mcp.tool()
    async def keyword_search(
        keywords: str,
        project: str | None = None,
        doc_type: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Search conversations by keywords (full-text search).

        Args:
            keywords: Keywords to search for in content
            project: Filter by project name (optional)
            doc_type: Filter by document type (optional)
            limit: Maximum results to return (default 10)
        """
        async with get_session() as session:
            # Simple ILIKE search for keywords
            search_pattern = f"%{keywords}%"

            stmt = (
                select(
                    Conversation.file_path,
                    Conversation.project_name,
                    Conversation.feature_name,
                    Conversation.doc_type,
                    Conversation.title,
                )
                .where(
                    or_(
                        Conversation.content.ilike(search_pattern),
                        Conversation.title.ilike(search_pattern),
                    )
                )
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )

            if project:
                stmt = stmt.where(Conversation.project_name == project)
            if doc_type:
                stmt = stmt.where(Conversation.doc_type == doc_type)

            result = await session.execute(stmt)
            rows = result.all()

            results = []
            for row in rows:
                results.append({
                    "file_path": row.file_path,
                    "project_name": row.project_name,
                    "feature_name": row.feature_name,
                    "doc_type": row.doc_type,
                    "title": row.title,
                })

            return {
                "keywords": keywords,
                "count": len(results),
                "results": results,
            }
