"""add pipl compliance fields

Revision ID: a1b2c3d4e5f6
Revises: 20bf856a3b6d
Create Date: 2026-08-21 17:00:00.000000

中国 PIPL（个人信息保护法）合规迁移
添加以下功能的字段：
1. 出生日期和年龄验证（儿童保护，第 35 条）
2. 监护人邮箱验证（14-18 岁用户）
3. 敏感数据加密存储
4. 用户同意记录
5. 数据删除和审计日志

【幂等性说明】
本迁移与历史迁移（1c3ca4810623 等）存在列定义重叠。为兼容已部分
建好的数据库，所有 add_column 均先检查列是否存在，create_table
使用 IF NOT EXISTS。可安全重复执行。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '20bf856a3b6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    """检查列是否已存在（幂等迁移辅助）。"""
    insp = inspect(conn)
    return column in {c['name'] for c in insp.get_columns(table)}


def _table_exists(conn, table: str) -> bool:
    """检查表是否已存在。"""
    insp = inspect(conn)
    return table in insp.get_table_names()


def upgrade() -> None:
    """Upgrade schema (idempotent)."""
    conn = op.get_bind()

    # === 1. 用户表：添加 PIPL 合规字段 ===
    if not _column_exists(conn, 'users', 'birthday'):
        op.add_column('users', sa.Column('birthday', sa.DateTime(), nullable=True,
            comment='用户出生日期（用于年龄验证和儿童保护，PIPL 第 35 条）'))
    if not _column_exists(conn, 'users', 'guardian_email'):
        op.add_column('users', sa.Column('guardian_email', sa.String(length=255), nullable=True,
            comment='监护人邮箱（14-18 岁用户需要，PIPL 第 35 条）'))
    if not _column_exists(conn, 'users', 'guardian_verified'):
        op.add_column('users', sa.Column('guardian_verified', sa.Boolean(), nullable=True, default=False,
            comment='监护人是否已验证（14-18 岁用户）'))
    if not _column_exists(conn, 'users', 'privacy_policy_accepted_at'):
        op.add_column('users', sa.Column('privacy_policy_accepted_at', sa.DateTime(), nullable=True,
            comment='用户同意隐私政策的时间'))
    if not _column_exists(conn, 'users', 'terms_of_service_accepted_at'):
        op.add_column('users', sa.Column('terms_of_service_accepted_at', sa.DateTime(), nullable=True,
            comment='用户同意服务条款的时间'))
    if not _column_exists(conn, 'users', 'ai_disclaimer_accepted_at'):
        op.add_column('users', sa.Column('ai_disclaimer_accepted_at', sa.DateTime(), nullable=True,
            comment='用户同意 AI 免责声明的时间'))

    # === 2. 危机事件表：支持加密存储 ===
    if not _column_exists(conn, 'crisis_events', 'created_at'):
        op.add_column('crisis_events', sa.Column('created_at', sa.DateTime(),
            server_default=sa.text('now()'), nullable=True,
            comment='危机事件被记录的时间'))
    if not _column_exists(conn, 'crisis_events', 'resolved_at'):
        op.add_column('crisis_events', sa.Column('resolved_at', sa.DateTime(), nullable=True,
            comment='危机事件被解决的时间'))
    if not _column_exists(conn, 'crisis_events', 'trigger_content_encrypted'):
        op.add_column('crisis_events', sa.Column('trigger_content_encrypted', sa.Text(), nullable=True,
            comment='加密的触发内容（JSON：{iv, ciphertext}）'))

    # === 3. 用户 API 配置表：支持加密存储 ===
    if not _column_exists(conn, 'user_api_configs', 'created_at'):
        op.add_column('user_api_configs', sa.Column('created_at', sa.DateTime(),
            server_default=sa.text('now()'), nullable=True,
            comment='API 配置创建时间'))
    if not _column_exists(conn, 'user_api_configs', 'api_key_encrypted'):
        op.add_column('user_api_configs', sa.Column('api_key_encrypted', sa.Text(), nullable=True,
            comment='加密的 API 密钥（JSON：{iv, ciphertext}）'))

    # === 4. 创建用户同意记录表 ===
    if not _table_exists(conn, 'user_consents'):
        op.create_table('user_consents',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('consent_type', sa.String(length=50), nullable=False,
                comment='同意类型：privacy_policy/tos/ai_disclaimer'),
            sa.Column('accepted', sa.Boolean(), nullable=False, default=True),
            sa.Column('version', sa.String(length=20), nullable=True, comment='政策版本'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_user_consents_id'), 'user_consents', ['id'], unique=False)
        op.create_index(op.f('ix_user_consents_user_id'), 'user_consents', ['user_id'], unique=False)
        op.create_index('idx_user_consent_type', 'user_consents', ['user_id', 'consent_type'], unique=False)

    # === 5. 创建用户数据删除请求表 ===
    if not _table_exists(conn, 'user_deletion_requests'):
        op.create_table('user_deletion_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, default='pending',
                comment='状态：pending/processing/completed'),
            sa.Column('requested_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('deletion_log', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                comment='删除详情日志'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_user_deletion_requests_id'), 'user_deletion_requests', ['id'], unique=False)
        op.create_index(op.f('ix_user_deletion_requests_user_id'), 'user_deletion_requests', ['user_id'], unique=False)
        op.create_index('idx_deletion_status', 'user_deletion_requests', ['status'], unique=False)

    # === 6. 添加审计日志索引优化 ===
    op.create_index('idx_audit_logs_event_type', 'audit_logs', ['event_type'], unique=False, if_not_exists=True)
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False, if_not_exists=True)


def downgrade() -> None:
    """Downgrade schema."""
    # 删除索引
    op.drop_index('idx_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_logs_event_type', table_name='audit_logs')

    # 删除表
    op.drop_index(op.f('ix_user_deletion_requests_user_id'), table_name='user_deletion_requests')
    op.drop_index(op.f('ix_user_deletion_requests_id'), table_name='user_deletion_requests')
    op.drop_index('idx_deletion_status', table_name='user_deletion_requests')
    op.drop_table('user_deletion_requests')

    op.drop_index('idx_user_consent_type', table_name='user_consents')
    op.drop_index(op.f('ix_user_consents_user_id'), table_name='user_consents')
    op.drop_index(op.f('ix_user_consents_id'), table_name='user_consents')
    op.drop_table('user_consents')

    # 删除列
    op.drop_column('user_api_configs', 'api_key_encrypted')
    op.drop_column('user_api_configs', 'created_at')

    op.drop_column('crisis_events', 'trigger_content_encrypted')
    op.drop_column('crisis_events', 'resolved_at')
    op.drop_column('crisis_events', 'created_at')

    op.drop_column('users', 'ai_disclaimer_accepted_at')
    op.drop_column('users', 'terms_of_service_accepted_at')
    op.drop_column('users', 'privacy_policy_accepted_at')
    op.drop_column('users', 'guardian_verified')
    op.drop_column('users', 'guardian_email')
    op.drop_column('users', 'birthday')
