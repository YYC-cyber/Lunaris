"""Add support for P1 features: message editing/forwarding/favorites, user blocking, appeals, sensitive words DB, crisis escalation, document sharing/permissions.

Revision ID: 0014_add_p1_features
Revises: 0013_add_user_moments_support
Create Date: 2026-08-21 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '0014_add_p1_features'
down_revision = '0013_add_user_moments_support'
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {item["name"] for item in inspect(bind).get_columns(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if not _column_exists(table, column.name):
        op.add_column(table, column)


def upgrade():
    """
    Add support for P1 features:
    1. Message editing (is_edited, edited_at)
    2. Message forwarding (forwarded_from_id)
    3. Message favorites (new table message_favorites)
    4. Message edit history (new table message_edit_history)
    5. User blocking (new table user_blocks)
    6. Appeals (new table appeals)
    7. Sensitive words DB (new table sensitive_words)
    8. Crisis escalation (escalation_status, assigned_to, escalated_at, resolved_at, resolution_notes)
    9. Document sharing (visibility, share_token, share_expires_at)
    10. Document permissions (new table document_permissions)
    11. Group chat @mentions (mentioned_user_ids)
    12. User bio field
    """
    # ============ 1. Messages table changes ============
    _add_column_if_missing('messages', sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'))
    _add_column_if_missing('messages', sa.Column('edited_at', sa.DateTime(), nullable=True))
    _add_column_if_missing('messages', sa.Column('forwarded_from_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_messages_forwarded_from_id',
        'messages',
        'messages',
        ['forwarded_from_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # ============ 2. Group messages table changes ============
    _add_column_if_missing('group_messages', sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'))
    _add_column_if_missing('group_messages', sa.Column('edited_at', sa.DateTime(), nullable=True))
    _add_column_if_missing('group_messages', sa.Column('forwarded_from_id', sa.Integer(), nullable=True))
    _add_column_if_missing('group_messages', sa.Column('mentioned_user_ids', postgresql.JSON(), nullable=True))
    op.create_foreign_key(
        'fk_group_messages_forwarded_from_id',
        'group_messages',
        'group_messages',
        ['forwarded_from_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # ============ 3. Message edit history table (new) ============
    op.create_table(
        'message_edit_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('old_content', sa.Text(), nullable=False),
        sa.Column('edited_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_message_edit_history_message_id', 'message_edit_history', ['message_id'])

    # ============ 4. Message favorites table (new) ============
    op.create_table(
        'message_favorites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='默认'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'message_id', name='uq_message_favorites_user_message'),
    )
    op.create_index('idx_message_favorites_user_id', 'message_favorites', ['user_id'])
    op.create_index('idx_message_favorites_created_at', 'message_favorites', ['created_at'])

    # ============ 5. User blocks table (new) ============
    op.create_table(
        'user_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('blocker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blocked_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blocker_id', 'blocked_id', name='uq_user_blocks_blocker_blocked'),
    )
    op.create_index('idx_user_blocks_blocker_id', 'user_blocks', ['blocker_id'])
    op.create_index('idx_user_blocks_blocked_id', 'user_blocks', ['blocked_id'])

    # ============ 6. Users table: add bio ============
    _add_column_if_missing('users', sa.Column('bio', sa.String(length=200), nullable=True))

    # ============ 7. Appeals table (new) ============
    op.create_table(
        'appeals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=True),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('admin_comment', sa.Text(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='ck_appeals_status'),
    )
    op.create_index('idx_appeals_user_id', 'appeals', ['user_id'])
    op.create_index('idx_appeals_status', 'appeals', ['status'])
    op.create_index('idx_appeals_created_at', 'appeals', ['created_at'])

    # ============ 8. Sensitive words table (new) ============
    op.create_table(
        'sensitive_words',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('effective_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('word', name='uq_sensitive_words_word'),
    )
    op.create_index('idx_sensitive_words_is_active', 'sensitive_words', ['is_active'])
    op.create_index('idx_sensitive_words_category', 'sensitive_words', ['category'])
    op.create_index('idx_sensitive_words_effective_at', 'sensitive_words', ['effective_at'])

    # ============ 9. Crisis events table changes ============
    _add_column_if_missing('crisis_events', sa.Column('escalation_status', sa.String(length=20), nullable=False, server_default='none'))
    _add_column_if_missing('crisis_events', sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True))
    _add_column_if_missing('crisis_events', sa.Column('escalated_at', sa.DateTime(), nullable=True))
    _add_column_if_missing('crisis_events', sa.Column('resolved_at', sa.DateTime(), nullable=True))
    _add_column_if_missing('crisis_events', sa.Column('resolution_notes', sa.Text(), nullable=True))
    op.create_foreign_key(
        'fk_crisis_events_assigned_to',
        'crisis_events',
        'users',
        ['assigned_to'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_check_constraint(
        'ck_crisis_events_escalation_status',
        'crisis_events',
        "escalation_status IN ('none', 'escalated', 'in_progress', 'resolved')",
    )

    # ============ 10. Documents table changes ============
    _add_column_if_missing('documents', sa.Column('visibility', sa.String(length=20), nullable=False, server_default='private'))
    _add_column_if_missing('documents', sa.Column('share_token', sa.String(length=64), nullable=True))
    _add_column_if_missing('documents', sa.Column('share_expires_at', sa.DateTime(), nullable=True))
    op.create_unique_constraint('uq_documents_share_token', 'documents', ['share_token'])
    op.create_check_constraint(
        'ck_documents_visibility',
        'documents',
        "visibility IN ('private', 'shared', 'public')",
    )

    # ============ 11. Document permissions table (new) ============
    op.create_table(
        'document_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_level', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'user_id', name='uq_document_permissions_doc_user'),
        sa.CheckConstraint("permission_level IN ('view', 'edit')", name='ck_document_permissions_level'),
    )
    op.create_index('idx_document_permissions_document_id', 'document_permissions', ['document_id'])
    op.create_index('idx_document_permissions_user_id', 'document_permissions', ['user_id'])


def downgrade():
    """Reverse the changes."""
    # ============ Document permissions table ============
    op.drop_index('idx_document_permissions_user_id', table_name='document_permissions')
    op.drop_index('idx_document_permissions_document_id', table_name='document_permissions')
    op.drop_table('document_permissions')

    # ============ Documents table ============
    op.drop_constraint('ck_documents_visibility', 'documents', type_='check')
    op.drop_constraint('uq_documents_share_token', 'documents', type_='unique')
    op.drop_column('documents', 'share_expires_at')
    op.drop_column('documents', 'share_token')
    op.drop_column('documents', 'visibility')

    # ============ Crisis events table ============
    op.drop_constraint('ck_crisis_events_escalation_status', 'crisis_events', type_='check')
    op.drop_constraint('fk_crisis_events_assigned_to', 'crisis_events', type_='foreignkey')
    op.drop_column('crisis_events', 'resolution_notes')
    op.drop_column('crisis_events', 'resolved_at')
    op.drop_column('crisis_events', 'escalated_at')
    op.drop_column('crisis_events', 'assigned_to')
    op.drop_column('crisis_events', 'escalation_status')

    # ============ Sensitive words table ============
    op.drop_index('idx_sensitive_words_effective_at', table_name='sensitive_words')
    op.drop_index('idx_sensitive_words_category', table_name='sensitive_words')
    op.drop_index('idx_sensitive_words_is_active', table_name='sensitive_words')
    op.drop_table('sensitive_words')

    # ============ Appeals table ============
    op.drop_index('idx_appeals_created_at', table_name='appeals')
    op.drop_index('idx_appeals_status', table_name='appeals')
    op.drop_index('idx_appeals_user_id', table_name='appeals')
    op.drop_table('appeals')

    # ============ Users table ============
    op.drop_column('users', 'bio')

    # ============ User blocks table ============
    op.drop_index('idx_user_blocks_blocked_id', table_name='user_blocks')
    op.drop_index('idx_user_blocks_blocker_id', table_name='user_blocks')
    op.drop_table('user_blocks')

    # ============ Message favorites table ============
    op.drop_index('idx_message_favorites_created_at', table_name='message_favorites')
    op.drop_index('idx_message_favorites_user_id', table_name='message_favorites')
    op.drop_table('message_favorites')

    # ============ Message edit history table ============
    op.drop_index('idx_message_edit_history_message_id', table_name='message_edit_history')
    op.drop_table('message_edit_history')

    # ============ Group messages table ============
    op.drop_constraint('fk_group_messages_forwarded_from_id', 'group_messages', type_='foreignkey')
    op.drop_column('group_messages', 'mentioned_user_ids')
    op.drop_column('group_messages', 'forwarded_from_id')
    op.drop_column('group_messages', 'edited_at')
    op.drop_column('group_messages', 'is_edited')

    # ============ Messages table ============
    op.drop_constraint('fk_messages_forwarded_from_id', 'messages', type_='foreignkey')
    op.drop_column('messages', 'forwarded_from_id')
    op.drop_column('messages', 'edited_at')
    op.drop_column('messages', 'is_edited')
