"""add group memories table

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'group_memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('soul_id', sa.Integer(), nullable=False),
        sa.Column('memory_type', sa.String(50), nullable=False),  # 'event', 'member_info', 'group_rule', etc
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['soul_id'], ['souls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_group_memories_group_soul', 'group_id', 'soul_id'),
    )


def downgrade() -> None:
    op.drop_table('group_memories')
