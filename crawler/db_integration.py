"""
Database Integration for IMS Scraper

This module handles saving crawl data to PostgreSQL database using ORM models.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

from database import (
    get_session,
    CrawlSession,
    Issue,
    SessionIssue,
    IssueComment,
    IssueHistory,
    Attachment,
    SearchQuery,
    SessionError,
    AuditLog
)
from config import settings

logger = logging.getLogger(__name__)


class DatabaseSaver:
    """Handles saving scraper data to PostgreSQL database"""

    def __init__(self, user_id: int, enabled: bool = True):
        """
        Initialize database saver

        Args:
            user_id: User ID for database operations
            enabled: Whether database saving is enabled
        """
        self.user_id = user_id
        self.enabled = enabled and settings.USE_DATABASE
        self.session_id = None
        self.session_uuid = str(uuid.uuid4())
        self.db_session = None  # Current database session object

        if self.enabled:
            logger.info(f"Database integration enabled for user_id={user_id}")
        else:
            logger.info("Database integration disabled")

    def create_session(
        self,
        product: str,
        original_query: str,
        parsed_query: str,
        max_results: int,
        crawl_related: bool,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Create a new crawl session in the database

        Args:
            product: Product name
            original_query: Original search query
            parsed_query: Parsed search query (IMS syntax)
            max_results: Maximum results to crawl
            crawl_related: Whether related issues are crawled
            session_metadata: Additional metadata

        Returns:
            Session ID if created, None otherwise
        """
        if not self.enabled:
            return None

        try:
            with get_session(user_id=self.user_id) as session:
                # Create session record
                db_session = CrawlSession(
                    session_uuid=self.session_uuid,
                    user_id=self.user_id,
                    product=product,
                    original_query=original_query,
                    parsed_query=parsed_query,
                    query_language='en',  # TODO: detect language
                    max_results=max_results,
                    crawl_related=crawl_related,
                    status='running',
                    started_at=datetime.now(timezone.utc),
                    session_metadata=session_metadata or {}
                )

                session.add(db_session)
                session.commit()

                self.session_id = db_session.session_id
                self.db_session = db_session

                logger.info(f"Created database session: {self.session_id} (UUID: {self.session_uuid})")

                # Create audit log entry
                self._create_audit_log(
                    session,
                    action='session_created',
                    resource_type='session',
                    resource_id=self.session_uuid,
                    new_value={
                        'product': product,
                        'query': original_query,
                        'max_results': max_results
                    }
                )

                return self.session_id

        except Exception as e:
            logger.error(f"Failed to create session in database: {e}")
            return None

    def save_search_query(
        self,
        original_query: str,
        parsed_query: str,
        results_count: int,
        product: str,
        parsing_method: Optional[str] = None,
        parsing_confidence: Optional[float] = None
    ) -> None:
        """
        Save search query to database

        Args:
            original_query: Original search query
            parsed_query: Parsed query
            results_count: Number of results found
            product: Product name
            parsing_method: Parsing method used (e.g., 'rule_based', 'llm')
            parsing_confidence: Confidence score (0-1)
        """
        if not self.enabled or not self.session_id:
            return

        try:
            with get_session(user_id=self.user_id) as session:
                search_query = SearchQuery(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    original_query=original_query,
                    parsed_query=parsed_query,
                    query_language='en',
                    product=product,
                    results_count=results_count,
                    parsing_method=parsing_method,
                    parsing_confidence=parsing_confidence,
                    synonym_expanded=False,  # TODO: track this
                    intent_filtered=False
                )

                session.add(search_query)
                session.commit()

                logger.debug(f"Saved search query to database")

        except Exception as e:
            logger.error(f"Failed to save search query: {e}")

    def save_issue(
        self,
        issue_data: Dict[str, Any],
        crawl_order: Optional[int] = None,
        crawl_duration_ms: Optional[int] = None
    ) -> Optional[int]:
        """
        Save issue data to database

        Args:
            issue_data: Issue data dictionary
            crawl_order: Order in which issue was crawled
            crawl_duration_ms: Time taken to crawl issue (ms)

        Returns:
            Issue PK if saved, None otherwise
        """
        if not self.enabled or not self.session_id:
            return None

        try:
            with get_session(user_id=self.user_id) as session:
                # Check if issue already exists
                existing_issue = session.query(Issue).filter_by(
                    issue_id=issue_data.get('issue_id')
                ).first()

                if existing_issue:
                    # Update existing issue
                    issue_pk = self._update_issue(session, existing_issue, issue_data)
                else:
                    # Create new issue
                    issue_pk = self._create_issue(session, issue_data)

                # Create session-issue association
                if issue_pk and self.session_id:
                    self._create_session_issue(
                        session,
                        issue_pk,
                        crawl_order,
                        crawl_duration_ms
                    )

                # Save comments
                self._save_comments(session, issue_pk, issue_data.get('comments', []))

                # Save history
                self._save_history(session, issue_pk, issue_data.get('history', []))

                # Save attachments metadata (files already saved to disk)
                self._save_attachments(session, issue_pk, issue_data.get('attachments', []))

                session.commit()

                logger.debug(f"Saved issue {issue_data.get('issue_id')} to database (PK: {issue_pk})")

                return issue_pk

        except Exception as e:
            logger.error(f"Failed to save issue {issue_data.get('issue_id')}: {e}")
            return None

    def _create_issue(self, session, issue_data: Dict[str, Any]) -> int:
        """Create new issue in database"""
        issue = Issue(
            issue_id=issue_data.get('issue_id'),
            title=issue_data.get('title'),
            description=issue_data.get('description'),
            product=issue_data.get('product'),
            status=issue_data.get('status'),
            priority=issue_data.get('priority'),
            severity=issue_data.get('severity'),
            issue_type=issue_data.get('issue_type'),
            reporter=issue_data.get('reporter'),
            owner=issue_data.get('owner'),
            manager=issue_data.get('manager'),
            registered_date=self._parse_datetime(issue_data.get('registered_date')),
            modified_date=self._parse_datetime(issue_data.get('modified_date')),
            closed_date=self._parse_datetime(issue_data.get('closed_date')),
            project_code=issue_data.get('project_code'),
            project_name=issue_data.get('project_name'),
            site=issue_data.get('site'),
            customer=issue_data.get('customer'),
            found_version=issue_data.get('found_version'),
            fixed_version=issue_data.get('fixed_version'),
            target_version=issue_data.get('target_version'),
            full_data=issue_data,
            crawl_count=1
        )

        session.add(issue)
        session.flush()

        return issue.issue_pk

    def _update_issue(self, session, existing_issue: Issue, issue_data: Dict[str, Any]) -> int:
        """Update existing issue in database"""
        # Update fields
        existing_issue.title = issue_data.get('title', existing_issue.title)
        existing_issue.description = issue_data.get('description', existing_issue.description)
        existing_issue.status = issue_data.get('status', existing_issue.status)
        existing_issue.priority = issue_data.get('priority', existing_issue.priority)
        existing_issue.severity = issue_data.get('severity', existing_issue.severity)
        existing_issue.modified_date = self._parse_datetime(issue_data.get('modified_date')) or existing_issue.modified_date
        existing_issue.full_data = issue_data
        existing_issue.last_crawled_at = datetime.now(timezone.utc)
        existing_issue.crawl_count += 1

        return existing_issue.issue_pk

    def _create_session_issue(
        self,
        session,
        issue_pk: int,
        crawl_order: Optional[int],
        crawl_duration_ms: Optional[int]
    ) -> None:
        """Create session-issue association"""
        # Check if association already exists
        existing = session.query(SessionIssue).filter_by(
            session_id=self.session_id,
            issue_pk=issue_pk
        ).first()

        if not existing:
            session_issue = SessionIssue(
                session_id=self.session_id,
                issue_pk=issue_pk,
                crawl_order=crawl_order,
                crawl_duration_ms=crawl_duration_ms,
                had_errors=False
            )
            session.add(session_issue)

    def _save_comments(self, session, issue_pk: int, comments: List[Dict[str, Any]]) -> None:
        """Save issue comments"""
        # Delete existing comments for this issue
        session.query(IssueComment).filter_by(issue_pk=issue_pk).delete()

        # Add new comments
        for idx, comment in enumerate(comments, 1):
            issue_comment = IssueComment(
                issue_pk=issue_pk,
                comment_number=idx,
                author=comment.get('author'),
                content=comment.get('content'),
                commented_at=self._parse_datetime(comment.get('date'))
            )
            session.add(issue_comment)

    def _save_history(self, session, issue_pk: int, history: List[Dict[str, Any]]) -> None:
        """Save issue history"""
        # Delete existing history for this issue
        session.query(IssueHistory).filter_by(issue_pk=issue_pk).delete()

        # Add new history
        for hist in history:
            issue_history = IssueHistory(
                issue_pk=issue_pk,
                changed_by=hist.get('changed_by'),
                changed_at=self._parse_datetime(hist.get('date')),
                change_type=hist.get('change_type'),
                field_name=hist.get('field'),
                old_value=hist.get('old_value'),
                new_value=hist.get('new_value'),
                description=hist.get('description')
            )
            session.add(issue_history)

    def _save_attachments(self, session, issue_pk: int, attachments: List[Dict[str, Any]]) -> None:
        """Save attachment metadata"""
        for att in attachments:
            # Skip attachments without filename (required field)
            filename = att.get('filename')
            if not filename:
                logger.warning(f"Skipping attachment without filename for issue_pk={issue_pk}")
                continue

            # Check if attachment already exists
            existing = session.query(Attachment).filter_by(
                issue_pk=issue_pk,
                filename=filename
            ).first()

            if not existing:
                attachment = Attachment(
                    issue_pk=issue_pk,
                    session_id=self.session_id,
                    filename=filename,
                    file_type=att.get('file_type'),
                    file_size=att.get('file_size'),
                    file_path=att.get('file_path'),
                    download_url=att.get('url'),
                    downloaded=att.get('downloaded', False),
                    download_error=att.get('error'),
                    extracted_text=att.get('extracted_text'),
                    text_extracted=bool(att.get('extracted_text'))
                )
                session.add(attachment)

    def save_error(
        self,
        error_type: str,
        error_message: str,
        severity: str = 'error',
        error_detail: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save error to database

        Args:
            error_type: Type of error
            error_message: Error message
            severity: Severity level ('error', 'warning', 'info')
            error_detail: Additional error details
        """
        if not self.enabled or not self.session_id:
            return

        try:
            with get_session(user_id=self.user_id) as session:
                session_error = SessionError(
                    session_id=self.session_id,
                    error_type=error_type,
                    severity=severity,
                    error_message=error_message,
                    error_detail=error_detail or {}
                )

                session.add(session_error)
                session.commit()

                logger.debug(f"Saved error to database: {error_type}")

        except Exception as e:
            logger.error(f"Failed to save error: {e}")

    def complete_session(
        self,
        status: str = 'completed',
        total_issues_found: int = 0,
        issues_crawled: int = 0,
        attachments_downloaded: int = 0,
        failed_issues: int = 0,
        related_issues: int = 0,
        search_time_ms: Optional[int] = None,
        crawl_time_ms: Optional[int] = None,
        avg_issue_time_ms: Optional[int] = None,
        parallel_workers: int = 1
    ) -> None:
        """
        Mark session as complete and update statistics

        Args:
            status: Final status ('completed', 'failed', 'cancelled')
            total_issues_found: Total issues found by search
            issues_crawled: Number of issues successfully crawled
            attachments_downloaded: Number of attachments downloaded
            failed_issues: Number of issues that failed to crawl
            related_issues: Number of related issues crawled
            search_time_ms: Time taken for search (ms)
            crawl_time_ms: Time taken for crawling (ms)
            avg_issue_time_ms: Average time per issue (ms)
            parallel_workers: Number of parallel workers used
        """
        if not self.enabled or not self.session_id:
            return

        try:
            with get_session(user_id=self.user_id) as session:
                db_session = session.get(CrawlSession, self.session_id)

                if db_session:
                    db_session.status = status
                    db_session.completed_at = datetime.now(timezone.utc)

                    # Calculate duration
                    if db_session.started_at:
                        duration = (db_session.completed_at - db_session.started_at).total_seconds()
                        db_session.duration_seconds = int(duration)

                    # Update statistics
                    db_session.total_issues_found = total_issues_found
                    db_session.issues_crawled = issues_crawled
                    db_session.attachments_downloaded = attachments_downloaded
                    db_session.failed_issues = failed_issues
                    db_session.related_issues = related_issues
                    db_session.search_time_ms = search_time_ms
                    db_session.crawl_time_ms = crawl_time_ms
                    db_session.avg_issue_time_ms = avg_issue_time_ms
                    db_session.parallel_workers = parallel_workers

                    session.commit()

                    logger.info(f"Session {self.session_id} marked as {status}")

                    # Create audit log entry
                    self._create_audit_log(
                        session,
                        action='session_completed',
                        resource_type='session',
                        resource_id=self.session_uuid,
                        new_value={
                            'status': status,
                            'issues_crawled': issues_crawled,
                            'duration_seconds': db_session.duration_seconds
                        }
                    )

        except Exception as e:
            logger.error(f"Failed to complete session: {e}")

    def _create_audit_log(
        self,
        session,
        action: str,
        resource_type: str,
        resource_id: str,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create audit log entry"""
        try:
            audit_log = AuditLog(
                user_id=self.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_value=old_value,
                new_value=new_value
            )
            session.add(audit_log)
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object"""
        if not date_str:
            return None

        try:
            # Try common date formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            # If all formats fail, return None
            logger.warning(f"Could not parse datetime: {date_str}")
            return None

        except Exception as e:
            logger.warning(f"Error parsing datetime '{date_str}': {e}")
            return None
