"""Add tts_cache table for TTS voice caching.

Revision ID: 0017_add_tts_cache_table
Revises: 0016_optimize_indexes
Create Date: 2026-08-22 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0017_add_tts_cache_table'
down_revision = '0016_optimize_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Create tts_cache table for voice synthesis caching."""
    op.create_table(
        'tts_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(length=64), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('voice_id', sa.String(length=50), nullable=True),
        sa.Column('voice_url', sa.Text(), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key', name='uq_tts_cache_cache_key'),
    )
    op.create_index('idx_tts_cache_cache_key', 'tts_cache', ['cache_key'])


def downgrade():
    """Drop tts_cache table."""
    op.drop_index('idx_tts_cache_cache_key', table_name='tts_cache')
    op.drop_table('tts_cache')
