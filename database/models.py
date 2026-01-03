"""
SQLAlchemy ORM Models for IMS Crawler Database

This module defines all database models using SQLAlchemy 2.0 declarative syntax.
All models use the 'ims' schema and include proper relationships.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    String, Integer, BigInteger, Text, Boolean, Numeric,
    TIMESTAMP, Date, JSON, CheckConstraint, UniqueConstraint,
    ForeignKey, Index
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)
from sqlalchemy.dialects.postgresql import INET, JSONB


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


# =============================================================================
# Table 1: Users
# =============================================================================

class User(Base):
    """User accounts and preferences"""
    __tablename__ = "users"
    __table_args__ = {"schema": "ims"}

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    department: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("role IN ('admin', 'user', 'readonly')"),
        default='user',
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferences: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    crawl_sessions: Mapped[List["CrawlSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    search_queries: Mapped[List["SearchQuery"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    analytics_daily: Mapped[List["AnalyticsDaily"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    analytics_monthly: Mapped[List["AnalyticsMonthly"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, username='{self.username}', role='{self.role}')>"


# =============================================================================
# Table 2: Crawl Sessions
# =============================================================================

class CrawlSession(Base):
    """Crawling session records"""
    __tablename__ = "crawl_sessions"
    __table_args__ = {"schema": "ims"}

    session_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_uuid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ims.users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    # Search configuration
    product: Mapped[str] = mapped_column(String(100), nullable=False)
    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_query: Mapped[str] = mapped_column(Text, nullable=False)
    query_language: Mapped[str] = mapped_column(String(10), default='en')
    max_results: Mapped[int] = mapped_column(Integer, default=100)
    crawl_related: Mapped[bool] = mapped_column(Boolean, default=False)

    # Execution info
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('running', 'completed', 'failed', 'cancelled')"),
        default='running',
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Results summary
    total_issues_found: Mapped[int] = mapped_column(Integer, default=0)
    issues_crawled: Mapped[int] = mapped_column(Integer, default=0)
    attachments_downloaded: Mapped[int] = mapped_column(Integer, default=0)
    failed_issues: Mapped[int] = mapped_column(Integer, default=0)
    related_issues: Mapped[int] = mapped_column(Integer, default=0)

    # Performance metrics
    search_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    crawl_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    avg_issue_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    parallel_workers: Mapped[int] = mapped_column(Integer, default=1)

    # Storage
    data_path: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata (renamed to avoid SQLAlchemy reserved word)
    session_metadata: Mapped[dict] = mapped_column(
        "metadata",  # Database column name
        JSONB,
        default={},
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="crawl_sessions")
    session_issues: Mapped[List["SessionIssue"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
    search_queries: Mapped[List["SearchQuery"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
    session_errors: Mapped[List["SessionError"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        back_populates="session"
    )

    def __repr__(self) -> str:
        return f"<CrawlSession(id={self.session_id}, uuid='{self.session_uuid}', status='{self.status}')>"


# =============================================================================
# Table 3: Issues
# =============================================================================

class Issue(Base):
    """IMS issue information"""
    __tablename__ = "issues"
    __table_args__ = {"schema": "ims"}

    issue_pk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    issue_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Basic info
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    product: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[Optional[str]] = mapped_column(String(50))
    priority: Mapped[Optional[str]] = mapped_column(String(20))
    severity: Mapped[Optional[str]] = mapped_column(String(20))
    issue_type: Mapped[Optional[str]] = mapped_column(String(50))

    # People
    reporter: Mapped[Optional[str]] = mapped_column(String(100))
    owner: Mapped[Optional[str]] = mapped_column(String(100))
    manager: Mapped[Optional[str]] = mapped_column(String(100))

    # Dates
    registered_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    modified_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    closed_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    # Project info
    project_code: Mapped[Optional[str]] = mapped_column(String(100))
    project_name: Mapped[Optional[str]] = mapped_column(String(200))
    site: Mapped[Optional[str]] = mapped_column(String(100))
    customer: Mapped[Optional[str]] = mapped_column(String(200))

    # Version info
    found_version: Mapped[Optional[str]] = mapped_column(String(100))
    fixed_version: Mapped[Optional[str]] = mapped_column(String(100))
    target_version: Mapped[Optional[str]] = mapped_column(String(100))

    # Full data
    full_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Tracking
    first_crawled_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    last_crawled_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    crawl_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    session_issues: Mapped[List["SessionIssue"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan"
    )
    comments: Mapped[List["IssueComment"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan"
    )
    history: Mapped[List["IssueHistory"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Issue(pk={self.issue_pk}, id='{self.issue_id}', title='{self.title[:50]}...')>"


# =============================================================================
# Table 4: Session Issues (Association Table)
# =============================================================================

class SessionIssue(Base):
    """Many-to-many mapping between sessions and issues"""
    __tablename__ = "session_issues"
    __table_args__ = (
        UniqueConstraint('session_id', 'issue_pk', name='uq_session_issue'),
        {"schema": "ims"}
    )

    session_issue_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ims.crawl_sessions.session_id", ondelete="CASCADE"),
        nullable=False
    )
    issue_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ims.issues.issue_pk", ondelete="CASCADE"),
        nullable=False
    )

    crawl_order: Mapped[Optional[int]] = mapped_column(Integer)
    crawl_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    had_errors: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    session: Mapped["CrawlSession"] = relationship(back_populates="session_issues")
    issue: Mapped["Issue"] = relationship(back_populates="session_issues")

    def __repr__(self) -> str:
        return f"<SessionIssue(session_id={self.session_id}, issue_pk={self.issue_pk})>"


# =============================================================================
# Table 5: Issue Comments
# =============================================================================

class IssueComment(Base):
    """Issue comments"""
    __tablename__ = "issue_comments"
    __table_args__ = {"schema": "ims"}

    comment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    issue_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ims.issues.issue_pk", ondelete="CASCADE"),
        nullable=False
    )

    comment_number: Mapped[Optional[int]] = mapped_column(Integer)
    author: Mapped[Optional[str]] = mapped_column(String(100))
    content: Mapped[Optional[str]] = mapped_column(Text)
    commented_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    issue: Mapped["Issue"] = relationship(back_populates="comments")

    def __repr__(self) -> str:
        return f"<IssueComment(id={self.comment_id}, issue_pk={self.issue_pk}, author='{self.author}')>"


# =============================================================================
# Table 6: Issue History
# =============================================================================

class IssueHistory(Base):
    """Issue change history"""
    __tablename__ = "issue_history"
    __table_args__ = {"schema": "ims"}

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    issue_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ims.issues.issue_pk", ondelete="CASCADE"),
        nullable=False
    )

    changed_by: Mapped[Optional[str]] = mapped_column(String(100))
    changed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    change_type: Mapped[Optional[str]] = mapped_column(String(50))
    field_name: Mapped[Optional[str]] = mapped_column(String(100))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    issue: Mapped["Issue"] = relationship(back_populates="history")

    def __repr__(self) -> str:
        return f"<IssueHistory(id={self.history_id}, issue_pk={self.issue_pk}, type='{self.change_type}')>"


# =============================================================================
# Table 7: Attachments
# =============================================================================

class Attachment(Base):
    """File attachments with text extraction"""
    __tablename__ = "attachments"
    __table_args__ = {"schema": "ims"}

    attachment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    issue_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ims.issues.issue_pk", ondelete="CASCADE"),
        nullable=False
    )
    session_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("ims.crawl_sessions.session_id", ondelete="SET NULL")
    )

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    file_path: Mapped[Optional[str]] = mapped_column(Text)

    download_url: Mapped[Optional[str]] = mapped_column(Text)
    downloaded: Mapped[bool] = mapped_column(Boolean, default=False)
    download_error: Mapped[Optional[str]] = mapped_column(Text)

    # Text extraction for RAG
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    text_extracted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    issue: Mapped["Issue"] = relationship(back_populates="attachments")
    session: Mapped[Optional["CrawlSession"]] = relationship(back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment(id={self.attachment_id}, filename='{self.filename}', downloaded={self.downloaded})>"


# =============================================================================
# Table 8: Search Queries
# =============================================================================

class SearchQuery(Base):
    """Search query history"""
    __tablename__ = "search_queries"
    __table_args__ = {"schema": "ims"}

    query_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ims.users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    session_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("ims.crawl_sessions.session_id", ondelete="CASCADE")
    )

    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_query: Mapped[Optional[str]] = mapped_column(Text)
    query_language: Mapped[Optional[str]] = mapped_column(String(10))

    product: Mapped[Optional[str]] = mapped_column(String(100))
    results_count: Mapped[Optional[int]] = mapped_column(Integer)

    # NL parsing info
    parsing_method: Mapped[Optional[str]] = mapped_column(String(50))
    parsing_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    synonym_expanded: Mapped[bool] = mapped_column(Boolean, default=False)
    intent_filtered: Mapped[bool] = mapped_column(Boolean, default=False)

    queried_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="search_queries")
    session: Mapped[Optional["CrawlSession"]] = relationship(back_populates="search_queries")

    def __repr__(self) -> str:
        return f"<SearchQuery(id={self.query_id}, query='{self.original_query[:50]}...', product='{self.product}')>"


# =============================================================================
# Table 9: Session Errors
# =============================================================================

class SessionError(Base):
    """Session errors and warnings"""
    __tablename__ = "session_errors"
    __table_args__ = {"schema": "ims"}

    error_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ims.crawl_sessions.session_id", ondelete="CASCADE"),
        nullable=False
    )

    error_type: Mapped[Optional[str]] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("severity IN ('error', 'warning', 'info')"),
        nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_detail: Mapped[Optional[dict]] = mapped_column(JSONB)

    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    session: Mapped["CrawlSession"] = relationship(back_populates="session_errors")

    def __repr__(self) -> str:
        return f"<SessionError(id={self.error_id}, session_id={self.session_id}, severity='{self.severity}')>"


# =============================================================================
# Table 10: Analytics Daily
# =============================================================================

class AnalyticsDaily(Base):
    """Daily statistics"""
    __tablename__ = "analytics_daily"
    __table_args__ = (
        UniqueConstraint('user_id', 'stat_date', name='uq_user_stat_date'),
        {"schema": "ims"}
    )

    stat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ims.users.user_id", ondelete="CASCADE")
    )
    stat_date: Mapped[datetime] = mapped_column(Date, nullable=False)

    # Session stats
    sessions_count: Mapped[int] = mapped_column(Integer, default=0)
    successful_sessions: Mapped[int] = mapped_column(Integer, default=0)
    failed_sessions: Mapped[int] = mapped_column(Integer, default=0)

    # Issue stats
    issues_crawled: Mapped[int] = mapped_column(Integer, default=0)
    unique_issues: Mapped[int] = mapped_column(Integer, default=0)
    new_issues: Mapped[int] = mapped_column(Integer, default=0)

    # Attachment stats
    attachments_downloaded: Mapped[int] = mapped_column(Integer, default=0)

    # Performance stats
    avg_session_duration_sec: Mapped[Optional[int]] = mapped_column(Integer)
    avg_issues_per_session: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    # Product breakdown
    product_stats: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    # Top queries
    top_queries: Mapped[list] = mapped_column(JSONB, default=[], nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="analytics_daily")

    def __repr__(self) -> str:
        return f"<AnalyticsDaily(id={self.stat_id}, user_id={self.user_id}, date={self.stat_date})>"


# =============================================================================
# Table 11: Analytics Monthly
# =============================================================================

class AnalyticsMonthly(Base):
    """Monthly statistics and trends"""
    __tablename__ = "analytics_monthly"
    __table_args__ = (
        UniqueConstraint('user_id', 'year', 'month', name='uq_user_year_month'),
        {"schema": "ims"}
    )

    stat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ims.users.user_id", ondelete="CASCADE")
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("month BETWEEN 1 AND 12"),
        nullable=False
    )

    # Session stats
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    avg_sessions_per_day: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    # Issue stats
    total_issues_crawled: Mapped[int] = mapped_column(Integer, default=0)
    unique_issues: Mapped[int] = mapped_column(Integer, default=0)

    # Trends
    keyword_trends: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    product_distribution: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    issue_status_breakdown: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    # Quality metrics
    avg_parsing_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    synonym_expansion_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="analytics_monthly")

    def __repr__(self) -> str:
        return f"<AnalyticsMonthly(id={self.stat_id}, user_id={self.user_id}, {self.year}-{self.month:02d})>"


# =============================================================================
# Table 12: Audit Log
# =============================================================================

class AuditLog(Base):
    """Audit log for all important operations"""
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "ims"}

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ims.users.user_id", ondelete="SET NULL")
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))
    resource_id: Mapped[Optional[str]] = mapped_column(String(100))

    old_value: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_value: Mapped[Optional[dict]] = mapped_column(JSONB)

    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.log_id}, user_id={self.user_id}, action='{self.action}')>"


# =============================================================================
# Helper Functions
# =============================================================================

def create_all_tables(engine):
    """
    Create all tables in the database

    Args:
        engine: SQLAlchemy engine

    Example:
        from sqlalchemy import create_engine
        from database.models import create_all_tables

        engine = create_engine('postgresql://user:pass@localhost/dbname')
        create_all_tables(engine)
    """
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """
    Drop all tables from the database (use with caution!)

    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.drop_all(engine)
