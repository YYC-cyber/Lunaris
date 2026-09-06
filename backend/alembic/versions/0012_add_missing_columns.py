"""add missing columns to group_chats

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, Sequence[str], None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 GroupRoleEnum 枚举
    op.execute("CREATE TYPE grouproleenum AS ENUM ('owner', 'admin', 'member')")

    # 添加 announcement 列
    op.add_column('group_chats', sa.Column('announcement', sa.Text(), nullable=True))

    # 为 group_members 添加 role 列
    op.add_column('group_members', sa.Column('role', sa.Enum('owner', 'admin', 'member', name='grouproleenum'), server_default='member', nullable=False))


def downgrade() -> None:
    op.drop_column('group_members', 'role')
    op.drop_column('group_chats', 'announcement')
    op.execute("DROP TYPE IF EXISTS grouproleenum")
