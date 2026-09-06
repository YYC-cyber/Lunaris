#!/usr/bin/env python3
"""
迁移脚本命名规范验证工具

用法：
    python scripts/validate_migrations.py              # 验证 alembic/versions/
    python scripts/validate_migrations.py --fix        # 修复简单的命名问题（可选）
"""

import os
import re
import sys
from pathlib import Path


def validate_migration_files(versions_dir="alembic/versions"):
    """
    验证迁移脚本的命名规范和内部结构。

    规范：
    - 文件名：NNNN_description.py（4位数字 + 下划线 + 描述）
    - revision 字符串应与文件名保持一致
    - down_revision 应指向前一个迁移
    """
    if not os.path.exists(versions_dir):
        print(f"❌ 错误: 目录不存在 {versions_dir}")
        return False

    # 获取所有迁移文件（排除 __init__.py）
    pattern = re.compile(r'^(\d{4})_[a-z0-9_]+\.py$')
    files = sorted([
        f for f in os.listdir(versions_dir)
        if f.endswith('.py') and f != '__init__.py' and not f.startswith('__pycache__')
    ])

    errors = []
    warnings = []

    # 检查文件名格式
    print("🔍 检查文件名格式...")
    for filename in files:
        if not pattern.match(filename):
            errors.append(f"❌ 无效的文件名格式: {filename}")

    # 检查序列号连续性
    print("🔍 检查序列号连续性...")
    for i, filename in enumerate(files, start=1):
        expected_seq = str(i).zfill(4)
        actual_seq = filename[:4]
        if actual_seq != expected_seq:
            errors.append(
                f"❌ 序列号不连续: {filename} (期望 {expected_seq}, 实际 {actual_seq})"
            )

    # 检查文件内容
    print("🔍 检查 revision 字符串...")
    for filename in files:
        filepath = os.path.join(versions_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()

        # 提取期望的 revision 名称（去掉 .py 后缀）
        expected_revision = filename[:-3]  # 移除 .py

        # 检查 revision 字符串
        if f"revision = '{expected_revision}'" not in content and \
           f'revision = "{expected_revision}"' not in content:
            warnings.append(
                f"⚠️  {filename}: revision 字符串不匹配 "
                f"(应为 '{expected_revision}')"
            )

        # 检查是否有 down_revision
        if 'down_revision' not in content:
            errors.append(f"❌ {filename}: 缺少 down_revision 定义")

    # 输出结果
    print("\n" + "="*60)
    if not errors and not warnings:
        print(f"✅ 验证通过！共 {len(files)} 个迁移脚本")
        return True
    else:
        if errors:
            print("错误:")
            for error in errors:
                print(f"  {error}")
        if warnings:
            print("\n警告:")
            for warning in warnings:
                print(f"  {warning}")
        return len(errors) == 0


def fix_migration_names(versions_dir="alembic/versions", dry_run=True):
    """
    尝试修复迁移脚本的文件名（如果可能）。

    Args:
        versions_dir: 迁移脚本目录
        dry_run: 如果 True，只显示将进行的更改；如果 False，实际进行修改
    """
    pattern = re.compile(r'^[a-z0-9]{8,}_[a-z0-9_]+\.py$')

    files = sorted([
        f for f in os.listdir(versions_dir)
        if f.endswith('.py') and f != '__init__.py'
    ])

    hash_files = [f for f in files if pattern.match(f)]

    if not hash_files:
        print("✅ 没有需要修复的文件")
        return

    print(f"发现 {len(hash_files)} 个使用 hash 风格命名的文件:\n")

    for i, filename in enumerate(hash_files, start=len(files) - len(hash_files) + 1):
        new_seq = str(i).zfill(4)
        # 提取描述部分（去掉 hash 前缀）
        parts = filename.split('_', 1)
        if len(parts) > 1:
            description = parts[1][:-3]  # 移除 .py
        else:
            description = "migrate"

        new_filename = f"{new_seq}_{description}.py"
        old_path = os.path.join(versions_dir, filename)
        new_path = os.path.join(versions_dir, new_filename)

        action = "将" if not dry_run else "将重命名"
        print(f"  {action}: {filename} → {new_filename}")

        if not dry_run:
            try:
                os.rename(old_path, new_path)
                print(f"    ✅ 成功")
            except Exception as e:
                print(f"    ❌ 失败: {e}")

    if dry_run:
        print("\n💡 这是预演模式。运行 `python scripts/validate_migrations.py --fix` 实际修改")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='验证和修复 Alembic 迁移脚本命名规范'
    )
    parser.add_argument(
        '--dir',
        default='alembic/versions',
        help='迁移脚本目录 (默认: alembic/versions)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='尝试修复命名问题'
    )

    args = parser.parse_args()

    if args.fix:
        fix_migration_names(args.dir, dry_run=True)
        response = input("\n是否继续修改? (y/n): ")
        if response.lower() == 'y':
            fix_migration_names(args.dir, dry_run=False)
    else:
        success = validate_migration_files(args.dir)
        sys.exit(0 if success else 1)
