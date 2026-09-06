#!/usr/bin/env python3
"""
scripts/init_db.py —— 一键初始化数据库：建库 → 启 pgvector → 迁移 → 种子角色。

【用法】（在仓库根目录执行）
    uv run python scripts/init_db.py
    或  python3 scripts/init_db.py

【前置】
- backend/.env 已配置 DATABASE_URL（含一个有 CREATEDB 权限的账号）
- 已安装依赖（uv sync）
- PostgreSQL 已安装并运行

【步骤】
1. 解析 backend/.env 的 DATABASE_URL
2. 连 postgres 维护库：CREATE DATABASE（幂等）
3. 连目标库：CREATE EXTENSION IF NOT EXISTS vector（pgvector）
4. 跑 alembic upgrade head（建表）
5. 写 6 个种子角色（复用 backend/scripts/init_souls.py）
"""
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

# 仓库根目录 / backend 目录
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from config.settings import get_settings  # noqa: E402


def _split_database_url(url: str) -> dict:
    """解析 SQLAlchemy 异步连接串（postgresql+asyncpg://user:pass@host:port/dbname）。"""
    # 去掉 +asyncpg 方言后缀，交给标准 urlsplit
    if "+" in url.split("://", 1)[0]:
        url = url.replace("+asyncpg", "", 1)
    p = urlsplit(url)
    return {
        "host": p.hostname or "localhost",
        "port": p.port or 5432,
        "user": p.username or "",
        "password": unquote(p.password or ""),
        "dbname": (p.path or "").lstrip("/"),
    }


def _admin_info(target_dbname: str) -> dict:
    """建库 / 启扩展需要超级用户。优先用 PG_ADMIN_URL，否则回退 DATABASE_URL 用户。"""
    url = os.environ.get("PG_ADMIN_URL", "")
    info = _split_database_url(url) if url else _split_database_url(get_settings().DATABASE_URL)
    info["dbname"] = target_dbname  # 目标库名始终取 .env 里的
    return info


def _connect(info: dict, dbname: str):
    """用 psycopg2 建立同步连接（脚本用，不走异步引擎）。"""
    import psycopg2
    return psycopg2.connect(
        host=info["host"],
        port=info["port"],
        user=info["user"],
        password=info["password"],
        dbname=dbname,
    )


def ensure_database(info: dict) -> None:
    """连 postgres 维护库建目标库（幂等）。"""
    from psycopg2 import sql as psql
    conn = _connect(info, "postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (info["dbname"],))
    if cur.fetchone() is None:
        cur.execute(psql.SQL("CREATE DATABASE {}").format(psql.Identifier(info["dbname"])))
        print(f"✅ 数据库 {info['dbname']} 已创建")
    else:
        print(f"⏭️  数据库 {info['dbname']} 已存在，跳过")
    cur.close()
    conn.close()


def ensure_vector_extension(info: dict) -> None:
    """连目标库启用 pgvector 扩展（幂等）。"""
    conn = _connect(info, info["dbname"])
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.close()
    conn.close()
    print(f"✅ pgvector 扩展已启用（{info['dbname']}）")


def run_alembic() -> None:
    """跑 alembic 迁移建表。"""
    print("🔄 执行 alembic upgrade head ...")
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic/alembic.ini", "upgrade", "head"],
        cwd=BACKEND,
        check=True,
    )
    print("✅ 数据库迁移完成")


def run_seed() -> None:
    """写种子角色（复用 backend/scripts/init_souls.py）。"""
    print("🔄 写入种子角色 ...")
    subprocess.run(
        [sys.executable, "scripts/init_souls.py"],
        cwd=BACKEND,
        check=True,
    )


def main() -> None:
    settings = get_settings()
    info = _split_database_url(settings.DATABASE_URL)
    if not info["dbname"]:
        sys.exit("❌ DATABASE_URL 缺少库名，请检查 backend/.env")

    # 建库 / 启 vector 扩展需要超级用户（PG_ADMIN_URL），迁移与种子用 .env 里的应用用户
    admin = _admin_info(info["dbname"])
    print(f"🎬 初始化数据库：{info['dbname']}（建库/扩展用 {admin['user']}@{admin['host']}:{admin['port']}）")
    try:
        ensure_database(admin)
        ensure_vector_extension(admin)
    except Exception as e:
        sys.exit(
            f"❌ 建库/启扩展失败：{e}\n"
            f"   提示：建库与 pgvector 扩展需要超级用户，请设置 PG_ADMIN_URL（如 "
            f"PG_ADMIN_URL=postgresql://postgres@localhost/postgres）后重试，或手动执行：\n"
            f"   CREATE DATABASE {info['dbname']};\n"
            f"   CREATE EXTENSION IF NOT EXISTS vector;（在 {info['dbname']} 库内）"
        )
    run_alembic()
    run_seed()
    print("🎉 数据库初始化完成！可启动后端：uv run uvicorn backend.main:app --reload")


if __name__ == "__main__":
    main()
