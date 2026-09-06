#!/usr/bin/env python3
"""
数据库同步脚本 —— 对齐 ORM 模型与真实数据库。

【背景】
迁移链存在历史分叉和列冲突（0012 与 0015 重复加 role、PIPL 迁移重复加列等）。
本脚本使用 SQLAlchemy 直接对比 models 元数据与数据库实际结构：
1. create_all() 创建缺失的表（不会动已存在的表）
2. 对已存在的表，幂等添加缺失的列（ALTER TABLE ADD COLUMN IF NOT EXISTS）
3. 对已存在的表，幂等创建缺失的索引

【特性】
- 幂等：可重复执行
- 每个列/索引操作单独 try，失败不影响其他操作
- NOT NULL 列自动添加 server_default（避免已有数据的表添加失败）
- 支持 --check 只检查

【用法】
    python scripts/sync_database.py            # 同步（幂等，可重复执行）
    python scripts/sync_database.py --check    # 仅检查差异，不修改
"""
import asyncio
import sys
from pathlib import Path

# 把 backend/ 加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine

import models  # noqa: F401  触发全部模型导入
from config.database import Base
from config.settings import get_settings


def _diff(sync_conn, metadata):
    """对比模型与数据库，返回 (缺失表, 每表缺失列)。"""
    insp = inspect(sync_conn)
    db_tables = set(insp.get_table_names())
    model_tables = set(metadata.tables.keys())

    missing_tables = model_tables - db_tables
    extra_tables = db_tables - model_tables

    missing_columns = {}
    for tname in model_tables & db_tables:
        db_cols = {c["name"] for c in insp.get_columns(tname)}
        model_cols = set(metadata.tables[tname].columns.keys())
        missing = model_cols - db_cols
        if missing:
            missing_columns[tname] = sorted(missing)

    return missing_tables, missing_columns, extra_tables


async def run(check_only: bool = False):
    s = get_settings()
    engine = create_async_engine(s.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            # 1. 检查差异
            def _get_diff(sync_conn):
                return _diff(sync_conn, Base.metadata)
            missing_tables, missing_columns, extra_tables = await conn.run_sync(_get_diff)

            print("=" * 60)
            print("数据库同步检查")
            print("=" * 60)
            print(f"模型表总数: {len(Base.metadata.tables)}")
            print(f"缺失表: {len(missing_tables)}")
            for t in sorted(missing_tables):
                print(f"  ❌ {t}")
            print(f"存在但缺列的表: {len(missing_columns)}")
            for t, cols in missing_columns.items():
                print(f"  ⚠️ {t}: 缺 {cols}")
            print(f"数据库多余表(未在模型中): {sorted(extra_tables)}")
            print()

            if check_only:
                return

        # 2. 创建缺失表（独立事务，每表单独提交）
        if missing_tables:
            async with engine.begin() as conn:
                def _create_all(sync_conn):
                    Base.metadata.create_all(sync_conn, tables=[
                        Base.metadata.tables[t] for t in sorted(missing_tables)
                    ])
                await conn.run_sync(_create_all)
            print(f"✅ 已创建 {len(missing_tables)} 张缺失表: {sorted(missing_tables)}")
            print()

        # 3. 添加缺失列（每列独立提交，失败不中断）
        if missing_columns:
            async with engine.begin() as conn:
                for tname in sorted(missing_columns.keys()):
                    tbl = Base.metadata.tables[tname]
                    for cname in sorted(missing_columns[tname]):
                        col = tbl.columns[cname]
                        try:
                            col_sql = f'"{cname}" {col.type.compile(dialect=engine.dialect)}'
                            # NOT NULL 且无默认值的列，加 DEFAULT（避免已有数据表失败）
                            nullable = col.nullable
                            default_clause = ""
                            if col.server_default is not None:
                                sd = col.server_default
                                if hasattr(sd, "arg"):
                                    arg = sd.arg
                                    if hasattr(arg, "text"):
                                        default_clause = f" DEFAULT {arg.text}"
                                    elif isinstance(arg, str):
                                        default_clause = f" DEFAULT '{arg}'"
                                    else:
                                        default_clause = f" DEFAULT {arg}"
                            elif not nullable:
                                # NOT NULL 无默认 → 用类型默认（字符串用 '', 布尔用 false, 数字用 0）
                                t = str(col.type).upper()
                                if "VARCHAR" in t or "TEXT" in t or "CHAR" in t:
                                    default_clause = " DEFAULT ''"
                                    nullable = True  # 加默认值后可置空，后续迁移处理
                                elif "BOOL" in t:
                                    default_clause = " DEFAULT false"
                                elif "INT" in t or "BIGINT" in t or "SMALLINT" in t:
                                    default_clause = " DEFAULT 0"
                                elif "JSON" in t:
                                    default_clause = " DEFAULT '[]'::jsonb"
                                    nullable = True
                                elif "TIMESTAMP" in t or "DATE" in t:
                                    nullable = True  # 时间戳允许空
                            n_clause = " NULL" if nullable else " NOT NULL"
                            sql = f'ALTER TABLE "{tname}" ADD COLUMN IF NOT EXISTS {col_sql}{n_clause}{default_clause}'
                            await conn.execute(text(sql))
                            print(f"  ✅ {tname}.{cname} 已添加")
                        except Exception as e:
                            print(f"  ⚠️ {tname}.{cname} 添加失败: {e}")

        # 4. 创建缺失索引
        async with engine.begin() as conn:
            def _create_indexes(sync_conn):
                insp = inspect(sync_conn)
                for tname in Base.metadata.tables.keys():
                    db_indexes = {ix["name"] for ix in insp.get_indexes(tname)}
                    for idx in Base.metadata.tables[tname].indexes:
                        if idx.name in db_indexes:
                            continue
                        cols = [c.name for c in idx.columns]
                        sql = f'CREATE INDEX IF NOT EXISTS "{idx.name}" ON "{tname}" ({", ".join(cols)})'
                        try:
                            sync_conn.execute(text(sql))
                            print(f"  ✅ 索引 {idx.name} on {tname} 已创建")
                        except Exception as e:
                            print(f"  ⚠️ 索引 {idx.name} 创建失败: {e}")
            await conn.run_sync(_create_indexes)

        if not missing_tables and not missing_columns:
            print("✅ 数据库已是最新结构，无需变更")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    check_only = "--check" in sys.argv
    asyncio.run(run(check_only=check_only))
