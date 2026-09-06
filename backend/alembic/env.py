# backend/alembic/env.py
"""Alembic 迁移环境（异步引擎）。

- DATABASE_URL 从 config.settings 注入（密钥不写进 alembic.ini）
- target_metadata 指向 config.database.Base（所有 ORM 模型继承它）
- 用法（在仓库根目录 backend/ 下）：
    alembic -c alembic/alembic.ini revision --autogenerate -m "描述"
    alembic -c alembic/alembic.ini upgrade head
"""
import asyncio
from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 把 backend/ 目录加入 Python 路径，保证 `config`、`models` 可导入（与运行目录无关）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import get_settings        # noqa: E402
from config.database import Base                 # noqa: E402
import models                                    # noqa: E402  触发 models/__init__.py 导入全部模型

settings = get_settings()

# Alembic 配置对象（来自 alembic.ini）
config = context.config

# 用 settings 里的 DATABASE_URL 覆盖（避免密钥写进 ini）
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 从 alembic.ini 读取日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 所有模型的元数据（autogenerate 依据它对比数据库）
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：不连数据库，仅生成 SQL。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """把迁移脚本执行到给定的同步连接上。"""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """在线模式：用 asyncpg 异步引擎执行迁移。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式入口（由 Alembic 调用）。"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
