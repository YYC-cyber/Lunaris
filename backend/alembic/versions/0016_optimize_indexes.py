"""Optimize database indexes for better query performance.

Revision ID: 0016_optimize_indexes
Revises: 0015_add_p2_features
Create Date: 2026-08-22 00:00:00.000000

Performance optimization migration:
1. Add full-text search indexes on message content and user bio/nickname
2. Add composite indexes for common query patterns
3. Ensure all foreign keys have indexes for efficient joins
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0016_optimize_indexes'
down_revision = '0015_add_p2_features'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance-optimized indexes."""

    # ============ 1. Full-text search indexes (using trigram GIN indexes) ============
    # These enable fast prefix/substring searches on common text fields

    # Enable pg_trgm extension if not already enabled
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # Message content search（使用 gin_trgm_ops 算子类）
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_content_trgm ON messages USING gin (content gin_trgm_ops)")

    # User nickname search
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_nickname_trgm ON users USING gin (nickname gin_trgm_ops)")

    # User bio search
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_bio_trgm ON users USING gin (bio gin_trgm_ops)")

    # ============ 2. Composite indexes for common query patterns ============

    # Appeal status + created_at for filtering and sorting
    op.create_index(
        'idx_appeals_status_created',
        'appeals',
        ['status', 'created_at'],
    )

    # Appeal user_id + status (common query: user's appeals by status)
    op.create_index(
        'idx_appeals_user_status',
        'appeals',
        ['user_id', 'status'],
    )

    # Group message query patterns: (group_id, created_at DESC)
    op.create_index(
        'idx_group_messages_group_created',
        'group_messages',
        ['group_id', 'created_at'],
    )

    # Group member queries: (group_id, joined_at)
    op.create_index(
        'idx_group_members_group_joined',
        'group_members',
        ['group_id', 'joined_at'],
    )

    # Group member by soul (for AI members in group)
    op.create_index(
        'idx_group_members_soul',
        'group_members',
        ['soul_id'],
    )

    # Timeline queries: (user_id, created_at DESC)
    op.create_index(
        'idx_moments_user_created_desc',
        'moments',
        ['user_id', 'created_at'],
    )

    # Soul timeline queries: (soul_id, created_at DESC)
    op.create_index(
        'idx_moments_soul_created_desc',
        'moments',
        ['soul_id', 'created_at'],
    )

    # Likes on a moment
    op.create_index(
        'idx_likes_moment_created',
        'likes',
        ['moment_id', 'created_at'],
    )

    # Comments on a moment (already exists in model, ensure it's present)
    # Index is already created in model definition, but document it

    # Message favorites queries: (user_id, category, created_at)
    op.create_index(
        'idx_message_favorites_user_category',
        'message_favorites',
        ['user_id', 'category'],
    )

    # Sticker favorites: (user_id, created_at)
    op.create_index(
        'idx_sticker_favorites_user',
        'sticker_favorites',
        ['user_id'],
    )

    # ============ 3. Ensure all foreign keys have indexes (for join performance) ============

    # These foreign keys should already have indexes from the original migrations,
    # but we verify/ensure they exist:
    # - messages(user_id) - already indexed in model
    # - messages(conversation_id) - already indexed in model
    # - messages(soul_id) - already indexed in model
    # - conversations(user1_id, user2_id) - already indexed in model
    # - comment(moment_id) - already indexed in model

    # Group chat related foreign keys
    op.create_index(
        'idx_group_chats_user',
        'group_chats',
        ['user_id'],
    )

    # Group invitations
    op.create_index(
        'idx_group_invitations_inviter',
        'group_invitations',
        ['inviter_id'],
    )

    op.create_index(
        'idx_group_invitations_invitee',
        'group_invitations',
        ['invitee_id'],
    )

    op.create_index(
        'idx_group_invitations_status',
        'group_invitations',
        ['status'],
    )

    # Group memories
    op.create_index(
        'idx_group_memories_group_soul',
        'group_memories',
        ['group_id', 'soul_id'],
    )

    op.create_index(
        'idx_group_memories_created',
        'group_memories',
        ['created_at'],
    )

    # ============ 4. Session/Online status indexes ============

    # User online status queries: (last_seen_at DESC)
    op.create_index(
        'idx_users_last_seen',
        'users',
        ['last_seen_at'],
    )

    # ============ 5. Sensitive word filters ============
    op.create_index(
        'idx_sensitive_words_word',
        'sensitive_words',
        ['word'],
        postgresql_using='hash',
    )

    print("✓ All performance indexes created successfully")


def downgrade():
    """Remove the added indexes."""

    # Drop all added indexes in reverse order
    indexes_to_drop = [
        ('idx_sensitive_words_word', 'sensitive_words'),
        ('idx_users_last_seen', 'users'),
        ('idx_group_memories_created', 'group_memories'),
        ('idx_group_memories_group_soul', 'group_memories'),
        ('idx_group_invitations_status', 'group_invitations'),
        ('idx_group_invitations_invitee', 'group_invitations'),
        ('idx_group_invitations_inviter', 'group_invitations'),
        ('idx_group_chats_user', 'group_chats'),
        ('idx_sticker_favorites_user', 'sticker_favorites'),
        ('idx_message_favorites_user_category', 'message_favorites'),
        ('idx_likes_moment_created', 'likes'),
        ('idx_moments_soul_created_desc', 'moments'),
        ('idx_moments_user_created_desc', 'moments'),
        ('idx_group_members_soul', 'group_members'),
        ('idx_group_members_group_joined', 'group_members'),
        ('idx_group_messages_group_created', 'group_messages'),
        ('idx_appeals_user_status', 'appeals'),
        ('idx_appeals_status_created', 'appeals'),
        ('idx_users_bio_trgm', 'users'),
        ('idx_users_nickname_trgm', 'users'),
        ('idx_messages_content_trgm', 'messages'),
    ]

    for idx_name, table_name in indexes_to_drop:
        try:
            op.drop_index(idx_name, table_name=table_name, if_exists=True)
        except Exception as e:
            print(f"Warning: Could not drop {idx_name}: {e}")
