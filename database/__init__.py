"""
Database Package for IMS Crawler

This package provides database connectivity and ORM models for the IMS Crawler system.

Components:
- db_config: Database configuration and connection management
- models: SQLAlchemy ORM models for all tables
"""

from database.db_config import (
    DatabaseConfig,
    DatabaseManager,
    get_db_manager,
    get_session
)

from database.models import (
    Base,
    User,
    CrawlSession,
    Issue,
    SessionIssue,
    IssueComment,
    IssueHistory,
    Attachment,
    SearchQuery,
    SessionError,
    AnalyticsDaily,
    AnalyticsMonthly,
    AuditLog,
    create_all_tables,
    drop_all_tables
)

__all__ = [
    # Configuration
    'DatabaseConfig',
    'DatabaseManager',
    'get_db_manager',
    'get_session',

    # Models
    'Base',
    'User',
    'CrawlSession',
    'Issue',
    'SessionIssue',
    'IssueComment',
    'IssueHistory',
    'Attachment',
    'SearchQuery',
    'SessionError',
    'AnalyticsDaily',
    'AnalyticsMonthly',
    'AuditLog',

    # Utilities
    'create_all_tables',
    'drop_all_tables',
]
