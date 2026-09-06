"""Add group chat tables for multi-user conversations.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0010'
down_revision = 'f1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 群聊表
    op.create_table(
        'group_chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_name', sa.String(length=100), nullable=True),
        sa.Column(
            'group_type',
            sa.Enum('AI_ONLY', 'HUMAN_ONLY', 'MIXED', name='grouptypeenum'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('auto_delete_hours', sa.Integer(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_chats_user_id'), 'group_chats', ['user_id'], unique=False)

    # 群成员表
    op.create_table(
        'group_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('member_type', sa.Enum('AI', 'HUMAN', name='membertypeenum'), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('soul_id', sa.Integer(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'INVITED', 'DECLINED', name='memberstatusenum'),
            nullable=False,
            server_default='ACTIVE',
        ),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['soul_id'], ['souls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_members_group_id'), 'group_members', ['group_id'], unique=False)
    op.create_index(op.f('ix_group_members_member_id'), 'group_members', ['member_id'], unique=False)

    # 群消息表
    op.create_table(
        'group_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('sender_type', sa.Enum('ai', 'user', name='sender_type_enum'), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('soul_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('voice_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['soul_id'], ['souls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_messages_group_id'), 'group_messages', ['group_id'], unique=False)
    op.create_index(op.f('ix_group_messages_created_at'), 'group_messages', ['created_at'], unique=False)

    # 邀请表
    op.create_table(
        'group_invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('inviter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invitee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'ACCEPTED', 'DECLINED', name='invitationstatusenum'),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['group_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invitee_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_invitations_group_id'), 'group_invitations', ['group_id'], unique=False)
    op.create_index(op.f('ix_group_invitations_invitee_id'), 'group_invitations', ['invitee_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_group_invitations_invitee_id'), table_name='group_invitations')
    op.drop_index(op.f('ix_group_invitations_group_id'), table_name='group_invitations')
    op.drop_table('group_invitations')

    op.drop_index(op.f('ix_group_messages_created_at'), table_name='group_messages')
    op.drop_index(op.f('ix_group_messages_group_id'), table_name='group_messages')
    op.drop_table('group_messages')

    op.drop_index(op.f('ix_group_members_member_id'), table_name='group_members')
    op.drop_index(op.f('ix_group_members_group_id'), table_name='group_members')
    op.drop_table('group_members')

    op.drop_index(op.f('ix_group_chats_user_id'), table_name='group_chats')
    op.drop_table('group_chats')
