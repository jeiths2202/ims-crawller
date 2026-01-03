"""
Database Configuration and Connection Management

This module provides database connection management using SQLAlchemy
for the IMS Crawler PostgreSQL database.
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """Database configuration from environment variables"""

    def __init__(self):
        self.host = os.getenv("DATABASE_HOST", "localhost")
        self.port = int(os.getenv("DATABASE_PORT", "5432"))
        self.name = os.getenv("DATABASE_NAME", "ims_crawler")
        self.user = os.getenv("DATABASE_USER", "ims_user")
        self.password = os.getenv("DATABASE_PASSWORD", "")
        self.schema = os.getenv("DATABASE_SCHEMA", "ims")

        # Connection pool settings
        self.pool_size = int(os.getenv("DATABASE_POOL_SIZE", "5"))
        self.max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
        self.pool_timeout = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))

        # Performance settings
        self.echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        self.echo_pool = os.getenv("DATABASE_ECHO_POOL", "false").lower() == "true"

    @property
    def connection_url(self) -> str:
        """Build PostgreSQL connection URL"""
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.name}"
        )

    def __repr__(self) -> str:
        return (
            f"DatabaseConfig(host={self.host}, port={self.port}, "
            f"name={self.name}, user={self.user}, schema={self.schema})"
        )


class DatabaseManager:
    """Database connection manager with session handling"""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database manager

        Args:
            config: Database configuration (uses defaults if None)
        """
        self.config = config or DatabaseConfig()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """Get or create SQLAlchemy engine"""
        if self._engine is None:
            self._engine = create_engine(
                self.config.connection_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=self.config.echo,
                echo_pool=self.config.echo_pool,
            )

            # Set search path to IMS schema
            @event.listens_for(self._engine, "connect")
            def set_search_path(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute(f"SET search_path TO {self.config.schema}, public")
                cursor.close()

        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    @contextmanager
    def session(self, user_id: Optional[int] = None) -> Generator[Session, None, None]:
        """
        Create a new database session with automatic cleanup

        Args:
            user_id: User ID for RLS context (required for ims_user role)

        Yields:
            SQLAlchemy session

        Example:
            with db_manager.session(user_id=123) as session:
                sessions = session.query(CrawlSession).all()
        """
        session = self.session_factory()

        try:
            # Set current user context for RLS
            if user_id is not None:
                session.execute(
                    text("SELECT ims.set_current_user(:user_id)"),
                    {"user_id": user_id}
                )

            yield session
            session.commit()

        except Exception as e:
            session.rollback()
            raise

        finally:
            session.close()

    def test_connection(self) -> bool:
        """
        Test database connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False

    def get_version(self) -> str:
        """
        Get PostgreSQL version

        Returns:
            PostgreSQL version string
        """
        with self.session() as session:
            result = session.execute(text("SELECT version()"))
            return result.scalar()

    def get_user_stats(self, user_id: int) -> dict:
        """
        Get comprehensive user statistics

        Args:
            user_id: User ID

        Returns:
            Dictionary with user statistics
        """
        with self.session(user_id=user_id) as session:
            result = session.execute(
                text("SELECT * FROM ims.get_user_stats(:user_id)"),
                {"user_id": user_id}
            )
            row = result.first()

            if row:
                return {
                    "total_sessions": row[0],
                    "successful_sessions": row[1],
                    "failed_sessions": row[2],
                    "total_issues_crawled": row[3],
                    "unique_issues": row[4],
                    "total_attachments": row[5],
                    "avg_session_duration_sec": float(row[6]) if row[6] else 0,
                    "last_session_date": row[7],
                    "most_used_product": row[8],
                }
            return {}

    def delete_old_sessions(self, user_id: int, older_than_days: int = 90) -> dict:
        """
        Delete sessions older than specified days

        Args:
            user_id: User ID
            older_than_days: Delete sessions older than this many days

        Returns:
            Dictionary with deletion counts
        """
        with self.session(user_id=user_id) as session:
            result = session.execute(
                text("SELECT * FROM ims.delete_old_sessions(:user_id, :days)"),
                {"user_id": user_id, "days": older_than_days}
            )
            row = result.first()

            if row:
                return {
                    "deleted_sessions": row[0],
                    "deleted_issues": row[1],
                    "deleted_attachments": row[2],
                }
            return {}

    def search_issues(
        self,
        search_query: str,
        product: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Full-text search for issues

        Args:
            search_query: Search query
            product: Filter by product (optional)
            limit: Maximum number of results

        Returns:
            List of matching issues
        """
        with self.session() as session:
            result = session.execute(
                text("SELECT * FROM ims.search_issues(:query, :product, :limit)"),
                {"query": search_query, "product": product, "limit": limit}
            )

            issues = []
            for row in result:
                issues.append({
                    "issue_pk": row[0],
                    "issue_id": row[1],
                    "title": row[2],
                    "description": row[3],
                    "product": row[4],
                    "status": row[5],
                    "rank": float(row[6]),
                })
            return issues

    def refresh_materialized_views(self) -> None:
        """Refresh all materialized views"""
        with self.session() as session:
            session.execute(text("SELECT ims.refresh_materialized_views()"))

    def aggregate_daily_stats(self, target_date: Optional[str] = None) -> None:
        """
        Aggregate daily statistics

        Args:
            target_date: Target date (YYYY-MM-DD) or None for yesterday
        """
        with self.session() as session:
            if target_date:
                session.execute(
                    text("SELECT ims.aggregate_daily_stats(:date)"),
                    {"date": target_date}
                )
            else:
                session.execute(text("SELECT ims.aggregate_daily_stats()"))

    def close(self) -> None:
        """Close database connections and dispose engine"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


@contextmanager
def get_session(user_id: Optional[int] = None) -> Generator[Session, None, None]:
    """
    Convenience function to get a database session

    Args:
        user_id: User ID for RLS context

    Yields:
        SQLAlchemy session

    Example:
        from database.db_config import get_session

        with get_session(user_id=123) as session:
            sessions = session.query(CrawlSession).all()
    """
    db_manager = get_db_manager()
    with db_manager.session(user_id=user_id) as session:
        yield session


if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    print("-" * 60)

    config = DatabaseConfig()
    print(f"Configuration: {config}")
    print()

    db = DatabaseManager(config)

    if db.test_connection():
        print("✓ Connection successful!")
        print()
        print(f"PostgreSQL version: {db.get_version()}")
        print()

        # Test user stats (will fail if user doesn't exist, that's OK)
        try:
            stats = db.get_user_stats(1)
            if stats:
                print("User statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"User stats test: {e}")

    else:
        print("✗ Connection failed!")
        print()
        print("Please check:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'ims_crawler' exists")
        print("  3. .env file has correct credentials")
        print("  4. User has correct permissions")

    db.close()
