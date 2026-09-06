#!/usr/bin/env python3
"""
Lunaris 数据库备份脚本

功能：
- 备份 PostgreSQL 数据库到指定目录（使用 pg_dump）
- 保留最近 N 份备份，自动清理旧备份
- 可选上传到 S3（如需远程备份，配置 AWS_* 环境变量）

用法：
    python scripts/backup_db.py                     # 备份到默认目录
    python scripts/backup_db.py --dir /backups       # 指定备份目录
    python scripts/backup_db.py --keep 14            # 保留最近 14 份

配合 cron 定时备份（每天凌晨 2 点）：
    0 2 * * * cd /path/to/lunaris/backend && .venv/bin/python scripts/backup_db.py >> logs/backup.log 2>&1
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 把 backend/ 加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parse_database_url(url: str):
    """解析 DATABASE_URL（postgresql+asyncpg://user:pass@host:port/db）。"""
    # 去掉 asyncpg 驱动后缀
    url = url.replace('postgresql+asyncpg://', 'postgresql://')
    url = url.replace('postgresql+psycopg2://', 'postgresql://')
    # 解析
    import urllib.parse
    parts = urllib.parse.urlparse(url)
    return {
        'host': parts.hostname or 'localhost',
        'port': parts.port or 5432,
        'user': parts.username or 'lunaris',
        'password': parts.password or '',
        'db': parts.path.lstrip('/') or 'lunaris',
    }


def run_backup(db_url: str, backup_dir: str, keep: int) -> Path:
    """执行 pg_dump 备份。"""
    info = parse_database_url(db_url)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"lunaris_{timestamp}.sql"

    # 构建 pg_dump 命令
    cmd = [
        'pg_dump',
        '-h', info['host'],
        '-p', str(info['port']),
        '-U', info['user'],
        '-d', info['db'],
        '-f', str(backup_file),
        '--format=custom',  # 压缩格式，支持选择性恢复
        '--no-owner',
    ]
    env = dict(os.environ)
    if info['password']:
        env['PGPASSWORD'] = info['password']

    print(f"🔍 开始备份数据库 {info['db']}@{info['host']}:{info['port']}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ 备份失败: {result.stderr}")
        sys.exit(1)

    size_mb = backup_file.stat().st_size / 1024 / 1024
    print(f"✅ 备份成功: {backup_file} ({size_mb:.1f} MB)")

    # 清理旧备份
    cleanup_old_backups(backup_dir, keep)
    return backup_file


def cleanup_old_backups(backup_dir: Path, keep: int):
    """保留最近 keep 份备份，删除更早的。"""
    backups = sorted(
        backup_dir.glob("lunaris_*.sql"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if len(backups) <= keep:
        return
    for old in backups[keep:]:
        try:
            old.unlink()
            print(f"🧹 清理旧备份: {old}")
        except OSError as e:
            print(f"⚠️ 清理失败: {old}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Lunaris 数据库备份")
    parser.add_argument('--dir', default='backups', help='备份目录（默认 backups/）')
    parser.add_argument('--keep', type=int, default=7, help='保留最近 N 份（默认 7）')
    args = parser.parse_args()

    # 从环境变量读取 DATABASE_URL
    from config.settings import get_settings
    settings = get_settings()
    db_url = settings.DATABASE_URL

    backup_file = run_backup(db_url, args.dir, args.keep)

    # 可选：上传到 S3（如配置了 AWS_ACCESS_KEY_ID）
    if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('S3_BUCKET'):
        try:
            import boto3
            s3 = boto3.client('s3')
            s3.upload_file(str(backup_file), os.environ['S3_BUCKET'], f"backups/{backup_file.name}")
            print(f"☁️ 已上传到 S3: s3://{os.environ['S3_BUCKET']}/backups/{backup_file.name}")
        except ImportError:
            print("⚠️ 未安装 boto3，跳过 S3 上传")
        except Exception as e:
            print(f"⚠️ S3 上传失败: {e}")

    print(f"\n📦 备份完成: {backup_file}")
    print(f"💡 恢复方法: pg_restore -h {parse_database_url(db_url)['host']} -d {parse_database_url(db_url)['db']} {backup_file}")


if __name__ == "__main__":
    main()
