#!/usr/bin/env python3
"""
Data Cleanup Script

Purpose: Programmatically fix data integrity issues found by check_data_health.py

Handles:
- Deletion of orphaned records
- Cleanup of constraint violations
- Repair of timestamp inconsistencies

Usage:
    python scripts/cleanup_orphaned_records.py [--dry-run] [--verbose]

Options:
    --dry-run: Show what would be deleted without actually deleting
    --verbose: Show detailed output of every operation
"""

import asyncio
import sys
from datetime import datetime
from typing import List, Dict, Any

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCleanup:
    """Performs data cleanup operations."""

    def __init__(self, database_url: str, dry_run: bool = False, verbose: bool = False):
        self.database_url = database_url
        self.dry_run = dry_run
        self.verbose = verbose
        self.engine = None
        self.session_factory = None
        self.cleanup_stats = {
            "orphaned_deleted": 0,
            "constraint_fixed": 0,
            "timestamps_repaired": 0,
            "total_operations": 0
        }

    async def connect(self):
        """Establish database connection."""
        self.engine = create_async_engine(self.database_url, echo=False)
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        logger.info("✓ Connected to database")

    async def disconnect(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("✓ Disconnected from database")

    async def execute(self, query: str) -> int:
        """Execute a DELETE or UPDATE query."""
        async with self.session_factory() as session:
            try:
                result = await session.execute(text(query))
                affected_rows = result.rowcount
                if not self.dry_run:
                    await session.commit()
                    self.cleanup_stats["total_operations"] += 1
                if self.verbose or affected_rows > 0:
                    logger.info(f"  → Affected rows: {affected_rows}")
                return affected_rows
            except Exception as e:
                logger.error(f"  ✗ Error executing query: {e}")
                await session.rollback()
                return 0

    async def cleanup_orphaned_records(self) -> int:
        """Delete orphaned records."""
        logger.info("Cleaning up orphaned records...")
        total_deleted = 0

        # Orphaned message_favorites (missing message)
        logger.info("  Deleting message_favorites with missing message...")
        query = """DELETE FROM message_favorites mf
                   WHERE mf.message_id NOT IN (SELECT id FROM messages)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned message_favorites (missing user)
        logger.info("  Deleting message_favorites with missing user...")
        query = """DELETE FROM message_favorites mf
                   WHERE mf.user_id NOT IN (SELECT id FROM users)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned appeals (missing user)
        logger.info("  Deleting appeals with missing user...")
        query = """DELETE FROM appeals a
                   WHERE a.user_id NOT IN (SELECT id FROM users)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned appeals (missing report)
        logger.info("  Deleting appeals with missing report...")
        query = """DELETE FROM appeals a
                   WHERE a.report_id IS NOT NULL
                   AND a.report_id NOT IN (SELECT id FROM reports)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned likes (missing moment)
        logger.info("  Deleting likes with missing moment...")
        query = """DELETE FROM likes l
                   WHERE l.moment_id NOT IN (SELECT id FROM moments)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned likes (missing user)
        logger.info("  Deleting likes with missing user...")
        query = """DELETE FROM likes l
                   WHERE l.user_id NOT IN (SELECT id FROM users)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned comments (missing moment)
        logger.info("  Deleting comments with missing moment...")
        query = """DELETE FROM comments c
                   WHERE c.moment_id NOT IN (SELECT id FROM moments)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned comments (missing parent_comment)
        logger.info("  Deleting comments with missing parent comment...")
        query = """DELETE FROM comments c
                   WHERE c.parent_comment_id IS NOT NULL
                   AND c.parent_comment_id NOT IN (SELECT id FROM comments)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned sticker_favorites (missing sticker)
        logger.info("  Deleting sticker_favorites with missing sticker...")
        query = """DELETE FROM sticker_favorites sf
                   WHERE sf.sticker_id NOT IN (SELECT id FROM stickers)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned sticker_favorites (missing user)
        logger.info("  Deleting sticker_favorites with missing user...")
        query = """DELETE FROM sticker_favorites sf
                   WHERE sf.user_id NOT IN (SELECT id FROM users)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned group_members (missing group)
        logger.info("  Deleting group_members with missing group...")
        query = """DELETE FROM group_members gm
                   WHERE gm.group_id NOT IN (SELECT id FROM group_chats)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned group_members (missing user)
        logger.info("  Deleting group_members with missing user...")
        query = """DELETE FROM group_members gm
                   WHERE gm.member_type = 'human' AND gm.member_id IS NOT NULL
                   AND gm.member_id NOT IN (SELECT id FROM users)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned group_messages (missing group)
        logger.info("  Deleting group_messages with missing group...")
        query = """DELETE FROM group_messages gm
                   WHERE gm.group_id NOT IN (SELECT id FROM group_chats)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        # Orphaned group_memories (missing group)
        logger.info("  Deleting group_memories with missing group...")
        query = """DELETE FROM group_memories gm
                   WHERE gm.group_id NOT IN (SELECT id FROM group_chats)"""
        deleted = await self.execute(query)
        total_deleted += deleted
        self.cleanup_stats["orphaned_deleted"] += deleted

        logger.info(f"✓ Cleaned {total_deleted} orphaned records")
        return total_deleted

    async def fix_constraint_violations(self) -> int:
        """Fix records that violate constraints."""
        logger.info("Fixing constraint violations...")
        total_fixed = 0

        # Messages with missing content - set default
        logger.info("  Fixing messages with missing content...")
        query = """UPDATE messages SET content = '[Deleted Content]'
                   WHERE content IS NULL OR content = ''"""
        fixed = await self.execute(query)
        total_fixed += fixed
        self.cleanup_stats["constraint_fixed"] += fixed

        # Moments with missing content - set default
        logger.info("  Fixing moments with missing content...")
        query = """UPDATE moments SET content = '[Deleted Content]'
                   WHERE content IS NULL OR content = ''"""
        fixed = await self.execute(query)
        total_fixed += fixed
        self.cleanup_stats["constraint_fixed"] += fixed

        # Comments with missing content - set default
        logger.info("  Fixing comments with missing content...")
        query = """UPDATE comments SET content = '[Deleted Content]'
                   WHERE content IS NULL OR content = ''"""
        fixed = await self.execute(query)
        total_fixed += fixed
        self.cleanup_stats["constraint_fixed"] += fixed

        logger.info(f"✓ Fixed {total_fixed} constraint violations")
        return total_fixed

    async def repair_timestamps(self) -> int:
        """Repair timestamp inconsistencies."""
        logger.info("Repairing timestamp inconsistencies...")
        total_repaired = 0

        # Messages with edited_at before created_at
        logger.info("  Fixing messages with edited_at < created_at...")
        query = """UPDATE messages SET edited_at = created_at + interval '1 second'
                   WHERE edited_at IS NOT NULL AND edited_at < created_at"""
        repaired = await self.execute(query)
        total_repaired += repaired
        self.cleanup_stats["timestamps_repaired"] += repaired

        # Appeals with reviewed_at before created_at
        logger.info("  Fixing appeals with reviewed_at < created_at...")
        query = """UPDATE appeals SET reviewed_at = created_at + interval '1 second'
                   WHERE reviewed_at IS NOT NULL AND reviewed_at < created_at"""
        repaired = await self.execute(query)
        total_repaired += repaired
        self.cleanup_stats["timestamps_repaired"] += repaired

        # Group messages with expires_at before created_at
        logger.info("  Fixing group_messages with expires_at < created_at...")
        query = """UPDATE group_messages
                   SET expires_at = created_at + interval '1 day'
                   WHERE expires_at IS NOT NULL AND expires_at < created_at"""
        repaired = await self.execute(query)
        total_repaired += repaired
        self.cleanup_stats["timestamps_repaired"] += repaired

        logger.info(f"✓ Repaired {total_repaired} timestamp issues")
        return total_repaired

    async def run_cleanup(self) -> Dict[str, Any]:
        """Run all cleanup operations."""
        logger.info("=" * 60)
        logger.info("Starting Database Cleanup")
        logger.info("=" * 60)

        if self.dry_run:
            logger.warning("⚠ DRY RUN MODE - No changes will be committed")

        await self.connect()

        try:
            await self.cleanup_orphaned_records()
            await self.fix_constraint_violations()
            await self.repair_timestamps()

            return {
                "timestamp": datetime.now().isoformat(),
                "dry_run": self.dry_run,
                "stats": self.cleanup_stats
            }

        finally:
            await self.disconnect()

    def print_summary(self, result: Dict[str, Any]):
        """Print cleanup summary."""
        print("\n" + "=" * 60)
        print("DATA CLEANUP SUMMARY")
        print("=" * 60)
        print(f"Timestamp: {result['timestamp']}")
        if result['dry_run']:
            print("Mode: DRY RUN (no changes committed)")
        print(f"\nOperations:")
        print(f"  Orphaned records deleted:  {result['stats']['orphaned_deleted']}")
        print(f"  Constraint violations fixed: {result['stats']['constraint_fixed']}")
        print(f"  Timestamp issues repaired: {result['stats']['timestamps_repaired']}")
        print(f"  Total operations: {result['stats']['total_operations']}")
        print("\n" + "=" * 60 + "\n")


async def main():
    """Main entry point."""
    import os
    from config.database import get_async_db_url

    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv

    try:
        database_url = get_async_db_url()
    except:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/lunaris"
        )

    if dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Cleanup cancelled")
            return 1

    cleanup = DataCleanup(database_url, dry_run=dry_run, verbose=verbose)
    result = await cleanup.run_cleanup()
    cleanup.print_summary(result)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
