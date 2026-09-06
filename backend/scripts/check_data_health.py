#!/usr/bin/env python3
"""
Data Integrity Check Script

Purpose: Programmatically check database integrity and report issues.
Detects:
- Orphaned records (foreign key references to deleted entities)
- Constraint violations (missing required fields)
- Timestamp inconsistencies
- Data quality issues

Usage:
    python scripts/check_data_health.py [--fix]
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, List, Any
from enum import Enum

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


class IssueType(Enum):
    """Types of data integrity issues."""
    ORPHANED = "ORPHANED"
    CONSTRAINT = "CONSTRAINT"
    TIMESTAMP = "TIMESTAMP"
    WARNING = "WARNING"


class DataIssue:
    """Represents a single data integrity issue."""

    def __init__(
        self,
        issue_type: IssueType,
        table: str,
        description: str,
        count: int,
        sample_ids: List[Any] = None,
        severity: str = "WARNING"
    ):
        self.issue_type = issue_type
        self.table = table
        self.description = description
        self.count = count
        self.sample_ids = sample_ids or []
        self.severity = severity  # WARNING, ERROR, CRITICAL
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.issue_type.value,
            "table": self.table,
            "description": self.description,
            "count": self.count,
            "sample_ids": self.sample_ids[:10],  # Limit to 10 samples
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat()
        }

    def __repr__(self) -> str:
        return f"<DataIssue {self.severity}: {self.description} ({self.count} affected)>"


class DataHealthChecker:
    """Performs comprehensive data integrity checks."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        self.issues: List[DataIssue] = []

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

    async def run_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results."""
        async with self.session_factory() as session:
            result = await session.execute(text(query))
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def check_orphaned_records(self) -> List[DataIssue]:
        """Check for orphaned records in the database."""
        logger.info("Checking for orphaned records...")
        orphan_checks = [
            # (description, query, severity)
            (
                "message_favorites with missing message",
                """SELECT mf.id FROM message_favorites mf
                   WHERE mf.message_id NOT IN (SELECT id FROM messages)""",
                "CRITICAL"
            ),
            (
                "message_favorites with missing user",
                """SELECT mf.id FROM message_favorites mf
                   WHERE mf.user_id NOT IN (SELECT id FROM users)""",
                "CRITICAL"
            ),
            (
                "appeals with missing user",
                """SELECT a.id FROM appeals a
                   WHERE a.user_id NOT IN (SELECT id FROM users)""",
                "CRITICAL"
            ),
            (
                "likes with missing moment",
                """SELECT l.id FROM likes l
                   WHERE l.moment_id NOT IN (SELECT id FROM moments)""",
                "CRITICAL"
            ),
            (
                "comments with missing moment",
                """SELECT c.id FROM comments c
                   WHERE c.moment_id NOT IN (SELECT id FROM moments)""",
                "CRITICAL"
            ),
            (
                "sticker_favorites with missing sticker",
                """SELECT sf.id FROM sticker_favorites sf
                   WHERE sf.sticker_id NOT IN (SELECT id FROM stickers)""",
                "ERROR"
            ),
            (
                "group_members with missing group",
                """SELECT gm.id FROM group_members gm
                   WHERE gm.group_id NOT IN (SELECT id FROM group_chats)""",
                "CRITICAL"
            ),
            (
                "group_messages with missing group",
                """SELECT gm.id FROM group_messages gm
                   WHERE gm.group_id NOT IN (SELECT id FROM group_chats)""",
                "CRITICAL"
            ),
        ]

        for description, query, severity in orphan_checks:
            try:
                results = await self.run_query(query)
                if results:
                    issue = DataIssue(
                        issue_type=IssueType.ORPHANED,
                        table=description.split(" with")[0],
                        description=description,
                        count=len(results),
                        sample_ids=[r['id'] for r in results],
                        severity=severity
                    )
                    self.issues.append(issue)
                    logger.warning(f"  ⚠ {issue}")
            except Exception as e:
                logger.error(f"  ✗ Error checking {description}: {e}")

        return self.issues

    async def check_constraint_violations(self) -> List[DataIssue]:
        """Check for constraint violations."""
        logger.info("Checking for constraint violations...")
        constraint_checks = [
            (
                "messages",
                "messages with missing content",
                "SELECT id FROM messages WHERE content IS NULL OR content = ''",
                "ERROR"
            ),
            (
                "moments",
                "moments with missing content",
                "SELECT id FROM moments WHERE content IS NULL OR content = ''",
                "ERROR"
            ),
            (
                "comments",
                "comments with missing content",
                "SELECT id FROM comments WHERE content IS NULL OR content = ''",
                "ERROR"
            ),
            (
                "users",
                "users with missing username",
                "SELECT id FROM users WHERE username IS NULL OR username = ''",
                "CRITICAL"
            ),
            (
                "users",
                "users with missing password_hash",
                "SELECT id FROM users WHERE password_hash IS NULL OR password_hash = ''",
                "CRITICAL"
            ),
        ]

        for table, description, query, severity in constraint_checks:
            try:
                results = await self.run_query(query)
                if results:
                    issue = DataIssue(
                        issue_type=IssueType.CONSTRAINT,
                        table=table,
                        description=description,
                        count=len(results),
                        sample_ids=[r['id'] for r in results],
                        severity=severity
                    )
                    self.issues.append(issue)
                    logger.warning(f"  ⚠ {issue}")
            except Exception as e:
                logger.error(f"  ✗ Error checking {description}: {e}")

        return self.issues

    async def check_timestamp_consistency(self) -> List[DataIssue]:
        """Check for timestamp inconsistencies."""
        logger.info("Checking for timestamp inconsistencies...")
        timestamp_checks = [
            (
                "messages",
                "messages with edited_at before created_at",
                "SELECT id FROM messages WHERE edited_at IS NOT NULL AND edited_at < created_at",
                "ERROR"
            ),
            (
                "appeals",
                "appeals with reviewed_at before created_at",
                "SELECT id FROM appeals WHERE reviewed_at IS NOT NULL AND reviewed_at < created_at",
                "ERROR"
            ),
            (
                "group_messages",
                "group_messages with expires_at before created_at",
                "SELECT id FROM group_messages WHERE expires_at IS NOT NULL AND expires_at < created_at",
                "ERROR"
            ),
        ]

        for table, description, query, severity in timestamp_checks:
            try:
                results = await self.run_query(query)
                if results:
                    issue = DataIssue(
                        issue_type=IssueType.TIMESTAMP,
                        table=table,
                        description=description,
                        count=len(results),
                        sample_ids=[r['id'] for r in results],
                        severity=severity
                    )
                    self.issues.append(issue)
                    logger.warning(f"  ⚠ {issue}")
            except Exception as e:
                logger.error(f"  ✗ Error checking {description}: {e}")

        return self.issues

    async def check_data_quality(self) -> Dict[str, int]:
        """Get data quality summary statistics."""
        logger.info("Collecting data quality metrics...")
        query = """
        SELECT 'messages' as entity, COUNT(*) as count FROM messages
        UNION ALL SELECT 'moments', COUNT(*) FROM moments
        UNION ALL SELECT 'comments', COUNT(*) FROM comments
        UNION ALL SELECT 'users', COUNT(*) FROM users
        UNION ALL SELECT 'likes', COUNT(*) FROM likes
        UNION ALL SELECT 'message_favorites', COUNT(*) FROM message_favorites
        UNION ALL SELECT 'group_chats', COUNT(*) FROM group_chats
        UNION ALL SELECT 'group_members', COUNT(*) FROM group_members
        UNION ALL SELECT 'group_messages', COUNT(*) FROM group_messages
        UNION ALL SELECT 'appeals', COUNT(*) FROM appeals
        ORDER BY entity
        """
        try:
            results = await self.run_query(query)
            summary = {r['entity']: r['count'] for r in results}
            logger.info("  ✓ Data quality metrics collected")
            return summary
        except Exception as e:
            logger.error(f"  ✗ Error collecting metrics: {e}")
            return {}

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all integrity checks."""
        logger.info("=" * 60)
        logger.info("Starting Database Integrity Check")
        logger.info("=" * 60)

        await self.connect()

        try:
            await self.check_orphaned_records()
            await self.check_constraint_violations()
            await self.check_timestamp_consistency()
            summary = await self.check_data_quality()

            # Generate report
            report = {
                "timestamp": datetime.now().isoformat(),
                "total_issues": len(self.issues),
                "issues_by_severity": {
                    "CRITICAL": len([i for i in self.issues if i.severity == "CRITICAL"]),
                    "ERROR": len([i for i in self.issues if i.severity == "ERROR"]),
                    "WARNING": len([i for i in self.issues if i.severity == "WARNING"]),
                },
                "issues": [i.to_dict() for i in self.issues],
                "summary": summary
            }

            return report

        finally:
            await self.disconnect()

    def print_report(self, report: Dict[str, Any]):
        """Print a formatted report."""
        print("\n" + "=" * 60)
        print("DATA INTEGRITY CHECK REPORT")
        print("=" * 60)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total Issues Found: {report['total_issues']}")
        print("\nIssue Summary:")
        print(f"  CRITICAL: {report['issues_by_severity']['CRITICAL']}")
        print(f"  ERROR:    {report['issues_by_severity']['ERROR']}")
        print(f"  WARNING:  {report['issues_by_severity']['WARNING']}")

        if report['issues']:
            print("\n" + "-" * 60)
            print("ISSUES FOUND:")
            print("-" * 60)
            for issue in report['issues']:
                print(f"\n{issue['severity']}: {issue['description']}")
                print(f"  Table: {issue['table']}")
                print(f"  Count: {issue['count']}")
                if issue['sample_ids']:
                    print(f"  Sample IDs: {issue['sample_ids'][:5]}")
        else:
            print("\n✓ No data integrity issues found!")

        if report['summary']:
            print("\n" + "-" * 60)
            print("DATA QUALITY SUMMARY:")
            print("-" * 60)
            for entity, count in sorted(report['summary'].items()):
                print(f"  {entity:20} {count:>10,}")

        print("\n" + "=" * 60 + "\n")

    def save_report(self, report: Dict[str, Any], filename: str = "data_integrity_report.json"):
        """Save report to JSON file."""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"✓ Report saved to {filename}")


async def main():
    """Main entry point."""
    # Get database URL from environment or use default
    import os
    from config.database import get_async_db_url

    try:
        database_url = get_async_db_url()
    except:
        # Fallback for when config is not available
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/lunaris"
        )

    checker = DataHealthChecker(database_url)
    report = await checker.run_all_checks()

    checker.print_report(report)
    checker.save_report(report)

    # Exit with appropriate code
    if report['issues_by_severity']['CRITICAL'] > 0:
        logger.error("CRITICAL issues found! Please investigate.")
        return 1
    elif report['issues_by_severity']['ERROR'] > 0:
        logger.warning("ERROR issues found! Please review.")
        return 1
    else:
        logger.info("✓ Database integrity check passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
