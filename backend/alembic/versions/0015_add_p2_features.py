"""Add support for P2 features: message search, group muting, permissions, online status, dark mode, etc.

Revision ID: 0015_add_p2_features
Revises: 0014_add_p1_features
Create Date: 2026-08-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0015_add_p2_features'
down_revision = '0014_add_p1_features'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add support for P2 features:
    1. Message search (no schema change, uses existing message table)
    2. Group muting (new table group_mutes)
    3. Group permissions matrix (new table group_permissions)
    4. Online status (users table add last_seen_at)
    5. Group announcements (new table group_announcements)
    6. UI preferences (users table add theme/font_size)
    """

    # ============ 1. Group mutes table (new) ============
    op.create_table(
        'group_mutes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('muted_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('muted_until', sa.DateTime(), nullable=False),
        sa.Column('muted_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['muted_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['muted_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'muted_user_id', name='uq_group_mutes_group_user'),
    )
    op.create_index('idx_group_mutes_group_id', 'group_mutes', ['group_id'])
    op.create_index('idx_group_mutes_muted_until', 'group_mutes', ['muted_until'])

    # ============ 2. Group permissions table (new) ============
    op.create_table(
        'group_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('can_invite', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_kick', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_edit_info', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_delete_messages', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_pin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_manage_roles', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'role', name='uq_group_permissions_group_role'),
    )
    op.create_index('idx_group_permissions_group_id', 'group_permissions', ['group_id'])

    # ============ 3. Group announcements table (new) ============
    op.create_table(
        'group_announcements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_group_announcements_group_id', 'group_announcements', ['group_id'])
    op.create_index('idx_group_announcements_is_pinned', 'group_announcements', ['is_pinned'])

    # ============ 4. Users table changes ============
    # Add last_seen_at for online status tracking
    op.add_column('users', sa.Column('last_seen_at', sa.DateTime(), nullable=True))

    # Add UI preferences
    op.add_column('users', sa.Column('theme', sa.String(length=20), nullable=False, server_default='light'))
    op.add_column('users', sa.Column('font_size', sa.String(length=20), nullable=False, server_default='normal'))

    # ============ 5. Moments table changes (for P2-04 privacy groups) ============
    op.add_column('moments', sa.Column('visible_groups', postgresql.JSON(), nullable=True))
    op.add_column('moments', sa.Column('hidden_user_ids', postgresql.JSON(), nullable=True))

    # ============ 6. Group members role 已由 0012 添加（覆盖 owner/admin/member），跳过 ============
    # 注：0012 使用 grouproleenum ENUM 类型；如需支持 guest，请改为 ALTER TYPE

    # ============ 7. Add search index on messages (for P2-01) ============
    # This is just a marker - actual full-text index can be added manually if needed
    # op.create_index('idx_messages_content_trgm', 'messages', ['content'], postgresql_using='gin')


def downgrade():
    """Reverse the changes."""
    # ============ Moments table ============
    op.drop_column('moments', 'hidden_user_ids')
    op.drop_column('moments', 'visible_groups')

    # ============ Users table ============
    op.drop_column('users', 'font_size')
    op.drop_column('users', 'theme')
    op.drop_column('users', 'last_seen_at')

    # ============ Group announcements table ============
    op.drop_index('idx_group_announcements_is_pinned', table_name='group_announcements')
    op.drop_index('idx_group_announcements_group_id', table_name='group_announcements')
    op.drop_table('group_announcements')

    # ============ Group permissions table ============
    op.drop_index('idx_group_permissions_group_id', table_name='group_permissions')
    op.drop_table('group_permissions')

    # ============ Group mutes table ============
    op.drop_index('idx_group_mutes_muted_until', table_name='group_mutes')
    op.drop_index('idx_group_mutes_group_id', table_name='group_mutes')
    op.drop_table('group_mutes')
