"""add group chat tables

Revision ID: f1c2d3e4f5a6
Revises: e88c68d3b565
Create Date: 2026-08-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '2d0381c12b34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """群聊表由后续 0010 迁移创建，保留此版本用于整理历史迁移链。"""
    pass


def downgrade() -> None:
    pass
