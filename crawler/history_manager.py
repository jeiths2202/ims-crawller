"""
Query History and Favorites Manager

Manages query history and favorite queries for IMS Crawler.
Stores query patterns, success rates, and user preferences.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class QueryRecord:
    """
    Record of a single query execution

    Attributes:
        query: The query string (original NL or IMS syntax)
        product: Product name
        parsed_query: Parsed IMS syntax (if NL query)
        language: Detected language (en/ko/ja)
        method: Parsing method (rules/llm/direct)
        confidence: Parsing confidence (0.0-1.0)
        results_count: Number of results returned
        timestamp: Query execution time
        execution_time: Query execution time in seconds
        is_favorite: Whether this query is marked as favorite
    """
    query: str
    product: str
    parsed_query: str
    language: str
    method: str
    confidence: float
    results_count: int
    timestamp: str
    execution_time: float
    is_favorite: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'QueryRecord':
        """Create QueryRecord from dictionary"""
        return cls(**data)


class HistoryManager:
    """
    Manages query history and favorites

    Features:
    - Automatic query history tracking
    - Favorite query management
    - Query statistics and analytics
    - Search history by product, language, date
    """

    def __init__(self, history_dir: Path = None):
        """
        Initialize history manager

        Args:
            history_dir: Directory for history files (default: data/history)
        """
        if history_dir is None:
            history_dir = Path("data/history")

        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.history_dir / "query_history.json"
        self.favorites_file = self.history_dir / "favorites.json"

        self.history: List[QueryRecord] = []
        self.favorites: List[QueryRecord] = []

        self._load_history()
        self._load_favorites()

    def _load_history(self):
        """Load query history from JSON file"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = [QueryRecord.from_dict(item) for item in data]
                logger.info(f"Loaded {len(self.history)} query records from history")
            except Exception as e:
                logger.error(f"Failed to load history: {e}")
                self.history = []
        else:
            self.history = []

    def _load_favorites(self):
        """Load favorites from JSON file"""
        if self.favorites_file.exists():
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.favorites = [QueryRecord.from_dict(item) for item in data]
                logger.info(f"Loaded {len(self.favorites)} favorite queries")
            except Exception as e:
                logger.error(f"Failed to load favorites: {e}")
                self.favorites = []
        else:
            self.favorites = []

    def _save_history(self):
        """Save query history to JSON file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                data = [record.to_dict() for record in self.history]
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.history)} query records")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def _save_favorites(self):
        """Save favorites to JSON file"""
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                data = [record.to_dict() for record in self.favorites]
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.favorites)} favorites")
        except Exception as e:
            logger.error(f"Failed to save favorites: {e}")

    def add_query(
        self,
        query: str,
        product: str,
        parsed_query: str,
        language: str,
        method: str,
        confidence: float,
        results_count: int,
        execution_time: float
    ) -> QueryRecord:
        """
        Add query to history

        Args:
            query: Original query string
            product: Product name
            parsed_query: Parsed IMS syntax
            language: Language code (en/ko/ja)
            method: Parsing method (rules/llm/direct)
            confidence: Parsing confidence
            results_count: Number of results
            execution_time: Execution time in seconds

        Returns:
            QueryRecord: The created record
        """
        record = QueryRecord(
            query=query,
            product=product,
            parsed_query=parsed_query,
            language=language,
            method=method,
            confidence=confidence,
            results_count=results_count,
            timestamp=datetime.now().isoformat(),
            execution_time=execution_time,
            is_favorite=False
        )

        self.history.append(record)
        self._save_history()

        logger.info(f"Added query to history: {query[:50]}...")
        return record

    def add_to_favorites(self, query_index: int = None, query_record: QueryRecord = None):
        """
        Add query to favorites

        Args:
            query_index: Index in history (0-based, -1 for last query)
            query_record: Direct QueryRecord to add
        """
        if query_record is None:
            if query_index is None:
                query_index = -1  # Default: last query

            if not self.history:
                raise ValueError("No queries in history")

            if abs(query_index) > len(self.history):
                raise ValueError(f"Invalid query index: {query_index}")

            query_record = self.history[query_index]

        # Check if already in favorites
        for fav in self.favorites:
            if fav.query == query_record.query and fav.product == query_record.product:
                logger.info(f"Query already in favorites: {query_record.query[:50]}...")
                return

        # Create copy and mark as favorite
        fav_record = QueryRecord(**query_record.to_dict())
        fav_record.is_favorite = True

        self.favorites.append(fav_record)
        self._save_favorites()

        logger.info(f"Added to favorites: {query_record.query[:50]}...")

    def remove_from_favorites(self, index: int):
        """
        Remove query from favorites

        Args:
            index: Index in favorites list
        """
        if 0 <= index < len(self.favorites):
            removed = self.favorites.pop(index)
            self._save_favorites()
            logger.info(f"Removed from favorites: {removed.query[:50]}...")
        else:
            raise ValueError(f"Invalid favorite index: {index}")

    def get_history(
        self,
        limit: int = 20,
        product: str = None,
        language: str = None,
        method: str = None
    ) -> List[QueryRecord]:
        """
        Get query history with optional filters

        Args:
            limit: Maximum number of records to return
            product: Filter by product name
            language: Filter by language (en/ko/ja)
            method: Filter by parsing method

        Returns:
            List of QueryRecord objects (most recent first)
        """
        filtered = self.history

        if product:
            filtered = [r for r in filtered if r.product == product]

        if language:
            filtered = [r for r in filtered if r.language == language]

        if method:
            filtered = [r for r in filtered if r.method == method]

        # Return most recent first
        return list(reversed(filtered[-limit:]))

    def get_favorites(self) -> List[QueryRecord]:
        """Get all favorite queries"""
        return self.favorites

    def search_history(self, search_term: str, limit: int = 10) -> List[QueryRecord]:
        """
        Search history by query text

        Args:
            search_term: Text to search for in queries
            limit: Maximum results

        Returns:
            List of matching QueryRecord objects
        """
        search_lower = search_term.lower()
        matches = [
            r for r in self.history
            if search_lower in r.query.lower() or search_lower in r.parsed_query.lower()
        ]

        return list(reversed(matches[-limit:]))

    def get_statistics(self) -> Dict:
        """
        Get query statistics

        Returns:
            Dictionary with various statistics
        """
        if not self.history:
            return {
                'total_queries': 0,
                'by_language': {},
                'by_product': {},
                'by_method': {},
                'avg_confidence': 0.0,
                'avg_results': 0.0,
                'avg_execution_time': 0.0
            }

        stats = {
            'total_queries': len(self.history),
            'favorites_count': len(self.favorites),
            'by_language': {},
            'by_product': {},
            'by_method': {},
            'avg_confidence': sum(r.confidence for r in self.history) / len(self.history),
            'avg_results': sum(r.results_count for r in self.history) / len(self.history),
            'avg_execution_time': sum(r.execution_time for r in self.history) / len(self.history)
        }

        # Count by language
        for record in self.history:
            stats['by_language'][record.language] = stats['by_language'].get(record.language, 0) + 1
            stats['by_product'][record.product] = stats['by_product'].get(record.product, 0) + 1
            stats['by_method'][record.method] = stats['by_method'].get(record.method, 0) + 1

        return stats

    def clear_history(self, keep_favorites: bool = True):
        """
        Clear query history

        Args:
            keep_favorites: If True, keep favorite queries
        """
        if keep_favorites:
            # Keep only favorites
            self.history = [r for r in self.history if r.is_favorite]
        else:
            self.history = []

        self._save_history()
        logger.info(f"Cleared history (kept {len(self.history)} favorites)")

    def export_history(self, output_file: Path, format: str = 'json'):
        """
        Export history to file

        Args:
            output_file: Output file path
            format: Export format ('json' or 'csv')
        """
        if format == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                data = [r.to_dict() for r in self.history]
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif format == 'csv':
            import csv
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if not self.history:
                    return

                fieldnames = list(self.history[0].to_dict().keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for record in self.history:
                    writer.writerow(record.to_dict())
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Exported {len(self.history)} records to {output_file}")
