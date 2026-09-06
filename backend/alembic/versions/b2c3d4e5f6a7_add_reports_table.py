"""add reports table for user reporting system

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-21 18:00:00.000000

中国网络安全法合规：添加用户举报系统
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # === 创建举报表 ===
    op.create_table('reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reporter_id', sa.UUID(), nullable=False, comment='举报人用户ID'),
        sa.Column('target_type', sa.String(length=20), nullable=False, comment='被举报对象类型：message/moment/profile/comment'),
        sa.Column('target_id', sa.Integer(), nullable=False, comment='被举报对象ID'),
        sa.Column('reason', sa.String(length=50), nullable=False, comment='举报原因：harassment/spam/violence/illegal/adult/scam/other'),
        sa.Column('description', sa.Text(), nullable=True, comment='举报详情描述'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending', comment='状态：pending/reviewing/approved/rejected/resolved'),
        sa.Column('reviewed_by', sa.UUID(), nullable=True, comment='审核人员ID'),
        sa.Column('review_comment', sa.Text(), nullable=True, comment='审核备注'),
        sa.Column('action_taken', sa.String(length=50), nullable=True, comment='处理方式：content_deleted/user_warned/user_suspended/none'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='举报时间'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True, comment='审核时间'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True, comment='解决时间'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index(op.f('ix_reports_id'), 'reports', ['id'], unique=False)
    op.create_index(op.f('ix_reports_reporter_id'), 'reports', ['reporter_id'], unique=False)
    op.create_index('idx_reports_status', 'reports', ['status'], unique=False)
    op.create_index('idx_reports_target', 'reports', ['target_type', 'target_id'], unique=False)
    op.create_index('idx_reports_created', 'reports', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_reports_created', table_name='reports')
    op.drop_index('idx_reports_target', table_name='reports')
    op.drop_index('idx_reports_status', table_name='reports')
    op.drop_index(op.f('ix_reports_reporter_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_id'), table_name='reports')
    op.drop_table('reports')
