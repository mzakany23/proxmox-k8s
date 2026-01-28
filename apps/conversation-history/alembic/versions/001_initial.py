"""Initial migration

Revision ID: 001_initial
Revises:
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('project_name', sa.String(200), nullable=False),
        sa.Column('feature_name', sa.String(200), nullable=True),
        sa.Column('doc_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('indexed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_path')
    )
    op.create_index('ix_conversations_project_name', 'conversations', ['project_name'])
    op.create_index('ix_conversations_doc_type', 'conversations', ['doc_type'])
    op.create_index('ix_conversations_feature_name', 'conversations', ['feature_name'])
    op.create_index('ix_conversations_content_hash', 'conversations', ['content_hash'])

    # Create conversation_chunks table
    op.create_table(
        'conversation_chunks',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chunks_conversation_id', 'conversation_chunks', ['conversation_id'])

    # Create index_status table
    op.create_table(
        'index_status',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_name', sa.String(200), nullable=True),
        sa.Column('last_index_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('files_indexed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('files_updated', sa.Integer(), server_default='0', nullable=False),
        sa.Column('files_failed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(20), server_default='idle', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('index_status')
    op.drop_table('conversation_chunks')
    op.drop_table('conversations')
    op.execute('DROP EXTENSION IF EXISTS vector')
