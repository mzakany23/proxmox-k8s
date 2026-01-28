"""Add source_id column for external source identification

Revision ID: 002_add_source_id
Revises: 001_initial
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_source_id'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source_id column for external source identification
    # Format: "agent-progress:workflow:{uuid}" for agent progress imports
    op.add_column(
        'conversations',
        sa.Column('source_id', sa.String(200), nullable=True)
    )
    op.create_index(
        'ix_conversations_source_id',
        'conversations',
        ['source_id']
    )


def downgrade() -> None:
    op.drop_index('ix_conversations_source_id', table_name='conversations')
    op.drop_column('conversations', 'source_id')
