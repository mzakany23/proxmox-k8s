"""SQLAlchemy ORM models with pgvector support."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Conversation(Base):
    """Conversation document model."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    feature_name: Mapped[str | None] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # checkpoint, instructions, docs, other
    title: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA256 for change detection
    source_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, index=True
    )  # External source ID, e.g. "agent-progress:workflow:{uuid}"
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    chunks: Mapped[list["ConversationChunk"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_conversations_project_name", "project_name"),
        Index("ix_conversations_doc_type", "doc_type"),
        Index("ix_conversations_feature_name", "feature_name"),
        Index("ix_conversations_content_hash", "content_hash"),
    )


class ConversationChunk(Base):
    """Chunked conversation content for better vector search."""

    __tablename__ = "conversation_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))

    # Relationships
    conversation: Mapped[Conversation] = relationship(back_populates="chunks")

    __table_args__ = (Index("ix_chunks_conversation_id", "conversation_id"),)


class IndexStatus(Base):
    """Track indexing status."""

    __tablename__ = "index_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_name: Mapped[str | None] = mapped_column(String(200))
    last_index_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    files_indexed: Mapped[int] = mapped_column(Integer, default=0)
    files_updated: Mapped[int] = mapped_column(Integer, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(20), default="idle"
    )  # idle, indexing, success, error
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
