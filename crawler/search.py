"""
Search Query Builder for IMS System
Supports IMS-specific search syntax
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class SearchQueryBuilder:
    """
    Builds search queries according to IMS search syntax

    IMS Search Syntax:
    1) Multiple keywords with space delimiter = OR search
       Example: "Tmax Tibero" → finds Tmax OR Tibero

    2) Plus operator (+) before word = AND search (no space between + and word)
       Example: "IMS +error" → finds IMS AND error

    3) Exact phrase with quotation marks
       Example: '"connection timeout"' → exact phrase match

    4) Combination of + and quotation marks
       Example: 'database +"connection error"' → database AND exact phrase "connection error"

    5) Keywords are highlighted in results

    6) Can search by Issue Number and Bug Number fields
    """

    @staticmethod
    def build_query(keywords: str, product: Optional[str] = None) -> str:
        """
        Build search query string

        Args:
            keywords: User-provided search keywords (already formatted with IMS syntax)
            product: Optional product name to filter by

        Returns:
            str: Formatted search query
        """
        query_parts = []

        # Add product filter if specified
        if product:
            # Product should be an AND condition
            query_parts.append(f"+{product}")

        # Add user keywords
        if keywords:
            query_parts.append(keywords.strip())

        query = " ".join(query_parts)
        logger.debug(f"Built search query: {query}")
        return query

    @staticmethod
    def build_or_query(keywords: List[str]) -> str:
        """
        Build OR query from list of keywords

        Args:
            keywords: List of keywords for OR search

        Returns:
            str: Space-delimited keywords (OR search)

        Example:
            build_or_query(['Tmax', 'Tibero']) → 'Tmax Tibero'
        """
        return " ".join(keywords)

    @staticmethod
    def build_and_query(required_keywords: List[str]) -> str:
        """
        Build AND query from list of required keywords

        Args:
            required_keywords: List of keywords that must all appear

        Returns:
            str: Plus-prefixed keywords (AND search)

        Example:
            build_and_query(['error', 'timeout']) → '+error +timeout'
        """
        return " ".join([f"+{kw}" for kw in required_keywords])

    @staticmethod
    def build_exact_phrase(phrase: str) -> str:
        """
        Build exact phrase query

        Args:
            phrase: Exact phrase to search

        Returns:
            str: Quoted phrase

        Example:
            build_exact_phrase('connection timeout') → '"connection timeout"'
        """
        # Remove existing quotes if any
        phrase = phrase.strip('"').strip("'")
        return f'"{phrase}"'

    @staticmethod
    def build_complex_query(
        or_keywords: Optional[List[str]] = None,
        and_keywords: Optional[List[str]] = None,
        exact_phrases: Optional[List[str]] = None
    ) -> str:
        """
        Build complex query combining OR, AND, and exact phrase searches

        Args:
            or_keywords: Keywords for OR search (space-delimited)
            and_keywords: Required keywords for AND search (+ prefix)
            exact_phrases: Exact phrases to search (quoted)

        Returns:
            str: Combined search query

        Example:
            build_complex_query(
                or_keywords=['Tmax', 'Tibero'],
                and_keywords=['error'],
                exact_phrases=['connection timeout']
            ) → 'Tmax Tibero +error +"connection timeout"'
        """
        parts = []

        if or_keywords:
            parts.append(SearchQueryBuilder.build_or_query(or_keywords))

        if and_keywords:
            parts.append(SearchQueryBuilder.build_and_query(and_keywords))

        if exact_phrases:
            for phrase in exact_phrases:
                parts.append(SearchQueryBuilder.build_exact_phrase(phrase))

        return " ".join(parts)

    @staticmethod
    def build_issue_number_query(issue_number: str) -> str:
        """
        Build query to search by issue number

        Args:
            issue_number: Issue or bug number

        Returns:
            str: Issue number query
        """
        return f"+{issue_number}"
