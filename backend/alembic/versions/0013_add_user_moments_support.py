"""Add user_id and visibility to moments table for user-authored moments support.

Revision ID: 0013_add_user_moments_support
Revises: 0012_add_missing_columns
Create Date: 2026-08-21 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0013_add_user_moments_support'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add support for user-authored moments:
    1. Make soul_id nullable (AI moments have soul_id, user moments have user_id)
    2. Add user_id column (FK to users.id)
    3. Add visibility column (public/friends/private)
    4. Add indexes for common queries
    """
    # 1. Make soul_id nullable
    op.alter_column(
        'moments',
        'soul_id',
        existing_type=sa.Integer(),
        nullable=True,
    )

    # 2. Add user_id column (FK to users.id, cascade delete)
    op.add_column('moments', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_moments_user_id',
        'moments',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )

    # 3. Add visibility column (enum-like, using String)
    op.add_column(
        'moments',
        sa.Column('visibility', sa.String(length=20), nullable=False, server_default='public'),
    )

    # 4. Add indexes for performance
    op.create_index(
        'idx_moments_user_id_created',
        'moments',
        ['user_id', 'created_at'],
    )
    op.create_index(
        'idx_moments_visibility',
        'moments',
        ['visibility'],
    )

    # 5. Add check constraints for data integrity
    op.create_check_constraint(
        'ck_moments_author_xor',
        'moments',
        "(user_id IS NOT NULL AND soul_id IS NULL) OR (user_id IS NULL AND soul_id IS NOT NULL)",
    )
    op.create_check_constraint(
        'ck_moments_visibility',
        'moments',
        "visibility IN ('public', 'friends', 'private')",
    )


def downgrade():
    """Reverse the changes."""
    # Remove check constraints
    op.drop_constraint('ck_moments_visibility', 'moments', type_='check')
    op.drop_constraint('ck_moments_author_xor', 'moments', type_='check')

    # Remove indexes
    op.drop_index('idx_moments_visibility', table_name='moments')
    op.drop_index('idx_moments_user_id_created', table_name='moments')

    # Remove foreign key and user_id column
    op.drop_constraint('fk_moments_user_id', 'moments', type_='foreignkey')
    op.drop_column('moments', 'user_id')

    # Remove visibility column
    op.drop_column('moments', 'visibility')

    # Make soul_id NOT NULL again
    op.alter_column(
        'moments',
        'soul_id',
        existing_type=sa.Integer(),
        nullable=False,
    )
