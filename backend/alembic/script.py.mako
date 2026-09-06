"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

本迁移脚本遵循命名规范 docs/MIGRATION_GUIDELINES.md
- 文件名格式：NNNN_description.py（例如：0016_add_column.py）
- revision 字符串与文件名保持一致
- down_revision 指向前一个迁移的 revision
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    # 最佳实践：
    # 1. 使用 server_default 为新列设置默认值
    # 2. 对大表使用 nullable=True，后续异步填充
    # 3. 包含适当的错误处理和日志记录
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    # 确保 downgrade 能够完全回滚 upgrade 的所有改动
    ${downgrades if downgrades else "pass"}

