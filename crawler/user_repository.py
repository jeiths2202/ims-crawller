"""
User Repository Module

Manages user-specific data storage with isolated repositories for each user.
Provides session management, report generation, and analytics tracking.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class SessionMetadata:
    """Metadata for a crawling session"""
    session_id: str
    user_id: str
    created_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None

    search_config: Dict[str, Any] = None
    results: Dict[str, Any] = None
    issue_ids: List[str] = None
    performance: Dict[str, Any] = None
    errors: List[str] = None
    warnings: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        """Create from dictionary"""
        return cls(**data)


class Session:
    """Represents a single crawling session"""

    def __init__(self, session_id: str, user_id: str, path: Path):
        self.session_id = session_id
        self.user_id = user_id
        self.path = path

        # Sub-directories
        self.issues_dir = path / "issues"
        self.attachments_dir = path / "attachments"
        self.metadata_file = path / "metadata.json"
        self.report_file = path / "session_report.md"

        # Ensure directories exist
        self.issues_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

        # Metadata
        self.metadata: Optional[SessionMetadata] = None
        self._load_metadata()

    def _load_metadata(self):
        """Load metadata from file if exists"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.metadata = SessionMetadata.from_dict(data)

    def init_metadata(
        self,
        product: str,
        original_query: str,
        parsed_query: str,
        language: str,
        max_results: int,
        crawl_related: bool = False
    ):
        """Initialize session metadata"""
        self.metadata = SessionMetadata(
            session_id=self.session_id,
            user_id=self.user_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            search_config={
                "product": product,
                "original_query": original_query,
                "parsed_query": parsed_query,
                "language": language,
                "max_results": max_results,
                "crawl_related": crawl_related
            },
            results={
                "total_issues": 0,
                "issues_crawled": 0,
                "attachments_downloaded": 0,
                "failed_issues": 0,
                "related_issues": 0
            },
            issue_ids=[],
            performance={},
            errors=[],
            warnings=[]
        )
        self._save_metadata()

    def update_results(
        self,
        total_issues: int = None,
        issues_crawled: int = None,
        attachments_downloaded: int = None,
        failed_issues: int = None,
        related_issues: int = None
    ):
        """Update session results"""
        if not self.metadata:
            return

        if total_issues is not None:
            self.metadata.results["total_issues"] = total_issues
        if issues_crawled is not None:
            self.metadata.results["issues_crawled"] = issues_crawled
        if attachments_downloaded is not None:
            self.metadata.results["attachments_downloaded"] = attachments_downloaded
        if failed_issues is not None:
            self.metadata.results["failed_issues"] = failed_issues
        if related_issues is not None:
            self.metadata.results["related_issues"] = related_issues

        self._save_metadata()

    def add_issue_id(self, issue_id: str):
        """Add an issue ID to the session"""
        if not self.metadata:
            return

        if issue_id not in self.metadata.issue_ids:
            self.metadata.issue_ids.append(issue_id)
            self._save_metadata()

    def add_error(self, error: str):
        """Add an error message"""
        if not self.metadata:
            return

        self.metadata.errors.append(error)
        self._save_metadata()

    def add_warning(self, warning: str):
        """Add a warning message"""
        if not self.metadata:
            return

        self.metadata.warnings.append(warning)
        self._save_metadata()

    def complete(self, start_time: datetime):
        """Mark session as completed"""
        if not self.metadata:
            return

        end_time = datetime.now(timezone.utc)
        self.metadata.completed_at = end_time.isoformat()

        # Handle both timezone-aware and timezone-naive start_time
        if start_time.tzinfo is None:
            # Assume UTC if no timezone info
            start_time = start_time.replace(tzinfo=timezone.utc)

        self.metadata.duration_seconds = int((end_time - start_time).total_seconds())
        self._save_metadata()

    def _save_metadata(self):
        """Save metadata to file"""
        if not self.metadata:
            return

        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata.to_dict(), f, ensure_ascii=False, indent=2)

    def get_issue_path(self, issue_id: str) -> Path:
        """Get path for an issue JSON file"""
        return self.issues_dir / f"{issue_id}.json"

    def get_attachment_dir(self, issue_id: str) -> Path:
        """Get directory path for issue attachments"""
        attach_dir = self.attachments_dir / issue_id
        attach_dir.mkdir(parents=True, exist_ok=True)
        return attach_dir

    @classmethod
    def from_path(cls, path: Path, user_id: str) -> "Session":
        """Create Session instance from existing path"""
        session_id = path.name
        return cls(session_id, user_id, path)


class UserRepository:
    """Manages user-specific data storage"""

    def __init__(self, user_id: str, base_path: Path = None):
        """
        Initialize user repository

        Args:
            user_id: User identifier (e.g., "yijae.shin")
            base_path: Base directory for all user data (default: data/users)
        """
        self.user_id = user_id
        self.base_path = base_path or Path("data/users")
        self.root = self.base_path / user_id

        # Sub-directories
        self.sessions_dir = self.root / "sessions"
        self.reports_dir = self.root / "reports"
        self.analytics_dir = self.root / "analytics"
        self.cache_dir = self.root / "cache"
        self.exports_dir = self.root / "exports"
        self.config_dir = self.root / "config"
        self.logs_dir = self.root / "logs"

        # Ensure structure exists
        self._ensure_structure()

    def _ensure_structure(self):
        """Create necessary directory structure"""
        dirs = [
            self.sessions_dir,
            self.reports_dir / "daily",
            self.reports_dir / "weekly",
            self.reports_dir / "monthly",
            self.reports_dir / "custom",
            self.analytics_dir,
            self.cache_dir,
            self.cache_dir / "embeddings",
            self.exports_dir / "json",
            self.exports_dir / "csv",
            self.exports_dir / "rag",
            self.config_dir,
            self.logs_dir
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def create_session(self, session_id: str) -> Session:
        """
        Create a new crawling session

        Args:
            session_id: Unique session identifier

        Returns:
            Session instance
        """
        session_path = self.sessions_dir / session_id
        return Session(
            session_id=session_id,
            user_id=self.user_id,
            path=session_path
        )

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get an existing session by ID

        Args:
            session_id: Session identifier

        Returns:
            Session instance if exists, None otherwise
        """
        session_path = self.sessions_dir / session_id
        if not session_path.exists():
            return None

        return Session.from_path(session_path, self.user_id)

    def get_sessions(self, limit: int = None, reverse: bool = True) -> List[Session]:
        """
        Get list of sessions (sorted by modification time)

        Args:
            limit: Maximum number of sessions to return
            reverse: If True, return newest first (default)

        Returns:
            List of Session instances
        """
        if not self.sessions_dir.exists():
            return []

        session_dirs = sorted(
            [d for d in self.sessions_dir.iterdir() if d.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=reverse
        )

        if limit:
            session_dirs = session_dirs[:limit]

        return [
            Session.from_path(d, self.user_id)
            for d in session_dirs
        ]

    def get_latest_session(self) -> Optional[Session]:
        """Get the most recent session"""
        sessions = self.get_sessions(limit=1)
        return sessions[0] if sessions else None

    def delete_session(self, session_id: str):
        """
        Delete a session and all its data

        Args:
            session_id: Session identifier
        """
        session_path = self.sessions_dir / session_id
        if session_path.exists():
            shutil.rmtree(session_path)

    def get_all_issue_ids(self) -> List[str]:
        """Get all unique issue IDs across all sessions"""
        issue_ids = set()

        for session in self.get_sessions():
            if session.metadata and session.metadata.issue_ids:
                issue_ids.update(session.metadata.issue_ids)

        return sorted(issue_ids)

    def find_sessions_by_product(self, product: str) -> List[Session]:
        """Find all sessions for a specific product"""
        matching_sessions = []

        for session in self.get_sessions():
            if (session.metadata and
                session.metadata.search_config and
                session.metadata.search_config.get("product") == product):
                matching_sessions.append(session)

        return matching_sessions

    def find_sessions_by_date(self, date: datetime.date) -> List[Session]:
        """Find all sessions for a specific date"""
        matching_sessions = []

        for session in self.get_sessions():
            if session.metadata and session.metadata.created_at:
                session_date = datetime.fromisoformat(
                    session.metadata.created_at
                ).date()
                if session_date == date:
                    matching_sessions.append(session)

        return matching_sessions

    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics for this user"""
        sessions = self.get_sessions()

        total_sessions = len(sessions)
        total_issues = 0
        total_attachments = 0
        products = {}
        issue_ids = set()

        for session in sessions:
            if session.metadata:
                # Count issues
                if session.metadata.results:
                    total_issues += session.metadata.results.get("issues_crawled", 0)
                    total_attachments += session.metadata.results.get(
                        "attachments_downloaded", 0
                    )

                # Count by product
                if session.metadata.search_config:
                    product = session.metadata.search_config.get("product", "Unknown")
                    products[product] = products.get(product, 0) + 1

                # Collect unique issue IDs
                if session.metadata.issue_ids:
                    issue_ids.update(session.metadata.issue_ids)

        return {
            "user_id": self.user_id,
            "total_sessions": total_sessions,
            "total_issues_crawled": total_issues,
            "unique_issues": len(issue_ids),
            "total_attachments": total_attachments,
            "sessions_by_product": products,
            "last_session": sessions[0].session_id if sessions else None
        }

    def save_config(self, config: Dict[str, Any]):
        """Save user configuration"""
        config_file = self.config_dir / "preferences.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def load_config(self) -> Dict[str, Any]:
        """Load user configuration"""
        config_file = self.config_dir / "preferences.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def __repr__(self):
        return f"UserRepository(user_id='{self.user_id}', root='{self.root}')"
