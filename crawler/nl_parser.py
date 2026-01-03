"""
Natural Language Query Parser for IMS Search

Converts natural language queries into IMS search syntax with support for:
- AND queries: "find error and crash" → "+error +crash"
- OR queries: "show connection or timeout" → "connection timeout"
- Exact phrases: "exact phrase 'out of memory'" → "'out of memory'"
- Mixed queries: "find error and crash or timeout" → "+error +crash timeout"

Supports English (Phase 1), Korean and Japanese (Phase 2+)
"""
import re
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

from crawler.nl_patterns import MultilingualPatterns
from crawler.search import SearchQueryBuilder
from crawler import prompts

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """
    Result of natural language query parsing

    Attributes:
        ims_query: Converted IMS syntax query
        confidence: Confidence score (0.0-1.0)
        method: Parsing method used ('rules' or 'llm')
        language: Detected language ('en', 'ko', 'ja')
        explanation: Human-readable explanation of parsing
        original_query: Original input query
    """
    ims_query: str
    confidence: float
    method: str
    language: str
    explanation: str
    original_query: str = ""


class ParsingError(Exception):
    """Exception raised when parsing fails"""
    pass


class LLMError(Exception):
    """Exception raised when LLM parsing fails"""
    pass


def is_ims_syntax(query: str) -> bool:
    """
    Detect if input is already IMS syntax vs natural language

    IMS Syntax Indicators:
    - Starts with + (e.g., "+error")
    - Contains quoted phrases (e.g., "'connection timeout'")
    - Numeric-only (e.g., "348115")
    - No natural language keywords

    Natural Language Indicators:
    - Contains verbs (find, search, show, get, 찾아, 보여, 検索)
    - Contains conjunctions (and, or, with, 와, 또는, と, または)
    - Contains question words (what, which, 무엇, どの)
    - Sentence structure

    Args:
        query: Input query string

    Returns:
        True if IMS syntax, False if natural language
    """
    query_stripped = query.strip()

    # Priority check: If starts with +, likely IMS syntax
    if query_stripped.startswith('+'):
        return True

    # Check for quoted phrases (single or double quotes)
    if "'" in query or '"' in query:
        return True

    # If numeric only, it's issue number (IMS syntax)
    if query_stripped.isdigit():
        return True

    # Check for natural language keywords
    nl_keywords = [
        # English
        'find', 'search', 'show', 'get', 'list', 'display',
        'with', 'and', 'or', 'that', 'have', 'has',
        'what', 'which', 'where', 'when', 'who', 'how',
        # Korean
        '찾아', '보여', '검색', '와', '과', '또는', '그리고',
        '무엇', '어떤', '어디', '언제',
        # Japanese
        '検索', '探す', '見せ', 'と', 'または', 'で',
        '何', 'どの', 'どこ', 'いつ'
    ]

    query_lower = query.lower()
    for keyword in nl_keywords:
        if keyword in query_lower:
            return False  # Natural language detected

    # Default: assume natural language for safety
    # (conservative approach - when unsure, parse it)
    return False


class NaturalLanguageParser:
    """
    Parse natural language queries into IMS syntax using rules

    Phase 1: English support with rule-based parsing
    Phase 2: Korean and Japanese support
    Phase 3: LLM fallback for complex queries
    """

    def __init__(self, llm_client=None):
        """
        Initialize NL parser

        Args:
            llm_client: Optional LLM client for fallback (Phase 3)
        """
        self.patterns = MultilingualPatterns()
        self.query_builder = SearchQueryBuilder()
        self.llm_client = llm_client

    def parse(self, query: str) -> ParseResult:
        """
        Main parsing pipeline: natural language → IMS syntax

        Args:
            query: Natural language query

        Returns:
            ParseResult with IMS syntax and metadata

        Raises:
            ParsingError: If parsing fails completely
        """
        if not query or not query.strip():
            raise ParsingError("Empty query")

        # Step 1: Detect language
        language = self._detect_language(query)
        logger.debug(f"Detected language: {language}")

        # Step 2: Try rule-based parsing
        result = self._parse_with_rules(query, language)

        # Step 3: LLM fallback if confidence < 0.7 (Phase 3)
        if result.confidence < 0.7 and self.llm_client:
            try:
                result = self._parse_with_llm(query, language)
            except LLMError as e:
                logger.warning(f"LLM fallback failed: {e}, using rules result")
                # Keep rules result even if LLM fails

        result.original_query = query
        return result

    def _detect_language(self, query: str) -> str:
        """
        Detect query language using character ranges

        Args:
            query: Input query

        Returns:
            Language code: 'en', 'ko', 'ja'
        """
        # Korean: Hangul Unicode range
        if re.search(r'[가-힣]', query):
            return 'ko'

        # Japanese: Hiragana, Katakana, Kanji
        if re.search(r'[ぁ-んァ-ヶ一-龯]', query):
            return 'ja'

        # Default: English
        return 'en'

    def _parse_with_rules(self, query: str, language: str) -> ParseResult:
        """
        Rule-based parsing with pattern matching

        Patterns to match:
        1. AND queries: "find A and B" → "+A +B"
        2. OR queries: "find A or B" → "A B"
        3. Exact phrases: "exact phrase X" → "'X'"
        4. Combined: "find A and B or C" → "+A +B C"

        Args:
            query: Natural language query
            language: Language code

        Returns:
            ParseResult with IMS syntax
        """
        patterns = self.patterns.get_patterns(language)

        # Extract intent (AND, OR, PHRASE, MIXED)
        intent, operators = self._detect_intent(query, patterns)

        # Extract terms (keywords to search)
        terms = self._extract_terms(query, patterns, language)

        # Build IMS query based on detected intent
        if intent == 'AND':
            # Pure AND query: all terms required
            ims_query = self._build_and_query(terms)
            explanation = f"AND query: {len(terms)} required terms"
            confidence = 0.9

        elif intent == 'OR':
            # Pure OR query: any term matches
            ims_query = self._build_or_query(terms)
            explanation = f"OR query: {len(terms)} optional terms"
            confidence = 0.9

        elif intent == 'PHRASE':
            # Exact phrase query
            ims_query = self._build_phrase_query(terms)
            explanation = f"Exact phrase query"
            confidence = 0.95

        elif intent == 'MIXED':
            # Mixed operators: parse AND/OR grouping
            ims_query = self._build_mixed_query(query, terms, patterns, language)

            # Count AND terms (with +) and OR terms (without +)
            and_count = ims_query.count('+')
            or_count = len(terms) - and_count

            if and_count > 0 and or_count > 0:
                explanation = f"Mixed query: {and_count} required (AND) + {or_count} optional (OR) terms"
                confidence = 0.8
            else:
                explanation = f"Mixed query: {len(terms)} terms"
                confidence = 0.75

        else:  # SIMPLE
            # No explicit operators: use smart query builder with synonym expansion
            ims_query, high_terms, medium_terms = self._build_smart_query(terms, language)
            if high_terms and medium_terms:
                explanation = f"Smart query: {len(high_terms)} required + {len(medium_terms)} optional terms"
                confidence = 0.75
            elif high_terms:
                explanation = f"Required terms: {len(high_terms)} terms"
                confidence = 0.8
            else:
                explanation = f"Simple query: {len(medium_terms)} terms"
                confidence = 0.6

        return ParseResult(
            ims_query=ims_query,
            confidence=confidence,
            method='rules',
            language=language,
            explanation=explanation
        )

    def _contains_keyword(self, query: str, keyword: str, language: str) -> bool:
        """
        Check if query contains keyword (language-aware)

        For English: Use word boundaries to avoid false matches
        For CJK (Korean/Japanese): Use simple substring matching

        Args:
            query: Query string (lowercase)
            keyword: Keyword to search for
            language: Language code

        Returns:
            True if keyword found
        """
        if language == 'en':
            # English: use word boundaries
            return re.search(rf'\b{re.escape(keyword)}\b', query) is not None
        else:
            # CJK languages: simple substring matching
            return keyword in query

    def _detect_intent(self, query: str, patterns: dict) -> Tuple[str, List[str]]:
        """
        Detect query intent (AND, OR, PHRASE, MIXED, SIMPLE)

        Args:
            query: Natural language query
            patterns: Language-specific patterns

        Returns:
            Tuple of (intent, list of operators found)
        """
        query_lower = query.lower()
        operators = []

        # Detect language from query
        language = self._detect_language(query)

        # Check for exact phrase indicators FIRST (highest priority)
        exact_keywords_sorted = sorted(patterns['exact_keywords'], key=len, reverse=True)
        has_exact = any(self._contains_keyword(query_lower, kw, language) for kw in exact_keywords_sorted)
        has_quotes = "'" in query or '"' in query
        if has_exact or has_quotes:
            # If it's ONLY a phrase query (no AND/OR), return PHRASE
            # Check if there are other operators (sorted by length to avoid partial matches)
            and_keywords_sorted = sorted(patterns['and_keywords'], key=len, reverse=True)
            or_keywords_sorted = sorted(patterns['or_keywords'], key=len, reverse=True)

            has_and_kw = any(self._contains_keyword(query_lower, kw, language) for kw in and_keywords_sorted)
            has_or_kw = any(self._contains_keyword(query_lower, kw, language) for kw in or_keywords_sorted)

            if not has_and_kw and not has_or_kw:
                return ('PHRASE', ['PHRASE'])
            else:
                operators.append('PHRASE')

        # Check for OR keywords FIRST (before AND) with longer keywords first
        # This is important for Japanese where "または" contains "また"
        or_keywords_sorted = sorted(patterns['or_keywords'], key=len, reverse=True)
        found_or_keywords = [kw for kw in or_keywords_sorted if self._contains_keyword(query_lower, kw, language)]

        # Check for AND keywords with longer keywords first
        and_keywords_sorted = sorted(patterns['and_keywords'], key=len, reverse=True)
        found_and_keywords = [kw for kw in and_keywords_sorted if self._contains_keyword(query_lower, kw, language)]

        # Remove AND keywords that are substrings of OR keywords (e.g., "また" within "または")
        if language in ['ja', 'ko']:
            # For CJK, filter out shorter AND keywords if they're part of longer OR keywords
            filtered_and_keywords = []
            for and_kw in found_and_keywords:
                is_substring = any(and_kw in or_kw for or_kw in found_or_keywords)
                if not is_substring:
                    filtered_and_keywords.append(and_kw)
            found_and_keywords = filtered_and_keywords

        if found_and_keywords:
            operators.append('AND')

        if found_or_keywords:
            operators.append('OR')

        # Determine intent
        if len(operators) == 0:
            return ('SIMPLE', operators)
        elif len(operators) == 1:
            return (operators[0], operators)
        else:
            return ('MIXED', operators)

    def _extract_terms(self, query: str, patterns: dict, language: str) -> List[str]:
        """
        Extract search terms from query

        Removes:
        - Verbs (find, search, show)
        - Operators (and, or)
        - Stopwords (the, a, is)
        - Exact phrase keywords

        Args:
            query: Natural language query
            patterns: Language-specific patterns
            language: Language code

        Returns:
            List of search terms
        """
        # Remove verbs (language-aware)
        cleaned = query
        for verb in patterns['verbs']:
            if language == 'en':
                cleaned = re.sub(rf'\b{re.escape(verb)}\b', '', cleaned, flags=re.IGNORECASE)
            else:
                # CJK: simple replacement
                cleaned = cleaned.replace(verb, '')

        # Remove AND/OR keywords (but preserve them for structure with delimiter)
        # Sort by length DESC to match longer keywords first (avoid partial matches)
        all_keywords = patterns['and_keywords'] + patterns['or_keywords']
        sorted_keywords = sorted(all_keywords, key=len, reverse=True)

        for kw in sorted_keywords:
            if language == 'en':
                cleaned = re.sub(rf'\b{re.escape(kw)}\b', ' | ', cleaned, flags=re.IGNORECASE)
            else:
                # CJK: replace keyword with delimiter
                cleaned = cleaned.replace(kw, ' | ')

        # Remove exact phrase keywords
        for kw in patterns['exact_keywords']:
            if language == 'en':
                cleaned = re.sub(rf'\b{re.escape(kw)}\b', '', cleaned, flags=re.IGNORECASE)
            else:
                # CJK: simple replacement
                cleaned = cleaned.replace(kw, '')

        # Extract quoted phrases first
        quoted_phrases = re.findall(r"'([^']+)'|\"([^\"]+)\"", cleaned)
        phrases = [p[0] or p[1] for p in quoted_phrases]

        # Remove quoted parts from cleaned string
        for phrase in phrases:
            cleaned = cleaned.replace(f"'{phrase}'", '')
            cleaned = cleaned.replace(f'"{phrase}"', '')

        # Split by pipe delimiter and clean
        parts = [p.strip() for p in cleaned.split('|') if p.strip()]

        # Extract individual terms
        terms = []
        for part in parts:
            if language == 'en':
                # English: split by spaces
                words = part.split()
            else:
                # CJK: split by spaces, but also handle no-space cases
                # For now, treat whole part as a word if no spaces
                words = part.split() if ' ' in part else [part]

            for word in words:
                word = word.strip('.,!?;:()[]{}')

                # Korean/Japanese-specific: remove trailing particles
                if language in ['ko', 'ja'] and word:
                    lang_patterns = self.patterns.get_patterns(language)
                    if 'particles' in lang_patterns:
                        # Sort particles by length (longest first) to avoid partial matches
                        particles_sorted = sorted(lang_patterns['particles'], key=len, reverse=True)
                        for particle in particles_sorted:
                            if word.endswith(particle):
                                word = word[:-len(particle)]
                                break

                # Filter out intent keywords (Korean-specific)
                # Intent keywords express what user wants to know, not actual search terms
                if language == 'ko' and word:
                    lang_patterns = self.patterns.get_patterns(language)
                    if word in lang_patterns.get('intent_keywords', []):
                        continue  # Skip intent keywords

                if word and not self.patterns.is_stopword(word, language):
                    terms.append(word)

        # Add quoted phrases back
        terms.extend(phrases)

        return terms

    def _expand_synonyms(self, term: str, language: str) -> str:
        """
        Expand English term to include Korean synonyms for better search coverage

        Args:
            term: Search term (e.g., "error")
            language: Language code

        Returns:
            Expanded term with synonyms (e.g., "error 에러 오류")
            or original term if no synonyms found

        Example:
            "error" → "error 에러 오류" (OR search in IMS)
            "TPETIME" → "TPETIME" (no synonyms, unchanged)
        """
        if language != 'ko':
            return term

        patterns = self.patterns.get_patterns('ko')
        synonyms_dict = patterns.get('synonyms', {})

        # Check if this term has synonyms
        term_lower = term.lower()
        if term_lower in synonyms_dict:
            synonym_list = synonyms_dict[term_lower]
            # Return space-separated synonyms (OR search in IMS)
            # e.g., "error 에러 오류"
            return ' '.join(synonym_list)

        return term

    def _build_and_query(self, terms: List[str]) -> str:
        """Build AND query: all terms required"""
        return ' '.join([f'+{term}' for term in terms])

    def _build_or_query(self, terms: List[str]) -> str:
        """Build OR query: any term matches"""
        return ' '.join(terms)

    def _build_phrase_query(self, terms: List[str]) -> str:
        """Build exact phrase query"""
        if len(terms) == 1:
            return f"'{terms[0]}'"
        else:
            # Multiple terms, join as phrase
            phrase = ' '.join(terms)
            return f"'{phrase}'"

    def _build_mixed_query(self, query: str, terms: List[str], patterns: dict, language: str) -> str:
        """
        Build mixed query with multiple operators

        Strategy:
        - Terms associated with AND keywords get + prefix (required)
        - Terms associated with OR keywords get no prefix (optional)

        Example: "error and crash or timeout"
        - "error and crash" → "+error +crash" (AND group)
        - "or timeout" → "timeout" (OR group)
        - Result: "+error +crash timeout"

        Args:
            query: Original query string
            terms: Extracted search terms
            patterns: Language patterns
            language: Language code

        Returns:
            IMS syntax query
        """
        # Get AND and OR keywords for this language
        and_keywords = patterns['and_keywords']
        or_keywords = patterns['or_keywords']

        # Split query by OR keywords first (they have lower precedence)
        query_lower = query.lower()

        # Find all OR keyword positions
        or_positions = []
        for or_kw in sorted(or_keywords, key=len, reverse=True):
            if language == 'en':
                pattern = rf'\b{re.escape(or_kw)}\b'
            else:
                pattern = re.escape(or_kw)

            for match in re.finditer(pattern, query_lower):
                or_positions.append(match.start())

        # If no OR keywords found, treat all as AND
        if not or_positions:
            return self._build_and_query(terms)

        # Split terms into AND groups and OR groups
        # Terms before any OR keyword are AND terms
        # Terms after OR keywords are OR terms
        and_terms = []
        or_terms = []

        # Find the position of each term in the original query
        for term in terms:
            # Find where this term appears in the query
            term_lower = term.lower()
            if language == 'en':
                pattern = rf'\b{re.escape(term_lower)}\b'
            else:
                pattern = re.escape(term_lower)

            match = re.search(pattern, query_lower)
            if match:
                term_pos = match.start()

                # Check if this term is before any OR keyword
                before_or = all(term_pos < or_pos for or_pos in or_positions)

                if before_or:
                    and_terms.append(term)
                else:
                    or_terms.append(term)

        # Build query: AND terms with +, OR terms without
        query_parts = []
        for term in and_terms:
            query_parts.append(f'+{term}')
        query_parts.extend(or_terms)

        return ' '.join(query_parts) if query_parts else ' '.join(terms)

    def _classify_term_priority(self, term: str, language: str) -> str:
        """
        Classify term priority for smart query building

        Priority Levels:
        - HIGH: Technical terms, error codes, product names (require ALL)
        - MEDIUM: General keywords (optional OR)
        - LOW: Context words, stopwords (remove)

        Args:
            term: Search term
            language: Language code

        Returns:
            Priority level: 'high', 'medium', or 'low'
        """
        patterns = self.patterns.get_patterns(language)

        # Check LOW priority first (remove these)
        if 'low_priority_words' in patterns:
            if term.lower() in patterns['low_priority_words']:
                return 'low'

        # Check HIGH priority patterns
        if 'high_priority_patterns' in patterns:
            for pattern in patterns['high_priority_patterns']:
                if re.match(pattern, term):
                    return 'high'

        # Default: MEDIUM priority
        return 'medium'

    def _build_smart_query(self, terms: List[str], language: str) -> Tuple[str, List[str], List[str]]:
        """
        Build smart query with priority-based AND/OR logic and synonym expansion

        Strategy:
        - High priority terms (error codes, tech terms): AND (+)
        - Medium priority terms (general keywords): OR (space)
        - Low priority terms (context words): removed
        - Synonym expansion: English terms expanded to include Korean equivalents

        Args:
            terms: Search terms
            language: Language code

        Returns:
            Tuple of (ims_query, high_priority_terms, medium_priority_terms)

        Example:
            Input: ["OpenFrame", "TPETIME", "error", "발생", "원인"]
            After synonym expansion: ["OpenFrame", "TPETIME", "error 에러 오류", ...]
            Output: "+TPETIME error 에러 오류", ["TPETIME"], ["error 에러 오류"]
        """
        high_priority = []
        medium_priority = []

        for term in terms:
            priority = self._classify_term_priority(term, language)

            if priority == 'high':
                # High priority terms: no synonym expansion (tech terms should be exact)
                high_priority.append(term)
            elif priority == 'medium':
                # Medium priority terms: expand with synonyms for better coverage
                expanded_term = self._expand_synonyms(term, language)
                medium_priority.append(expanded_term)
            # 'low' priority terms are skipped

        # Build query: high priority with +, medium priority without
        query_parts = []

        # Add high priority terms with AND operator
        for term in high_priority:
            query_parts.append(f'+{term}')

        # Add medium priority terms with OR operator (no prefix)
        # Expanded terms like "error 에러 오류" will work as OR in IMS
        query_parts.extend(medium_priority)

        ims_query = ' '.join(query_parts) if query_parts else ' '.join(terms)

        return ims_query, high_priority, medium_priority

    def _parse_with_llm(self, query: str, language: str) -> ParseResult:
        """
        LLM-based parsing for complex queries (Phase 3)

        Args:
            query: Natural language query
            language: Language code

        Returns:
            ParseResult from LLM

        Raises:
            LLMError: If LLM parsing fails
        """
        if not self.llm_client:
            raise LLMError("LLM client not available")

        try:
            # Build few-shot prompt for language
            prompt_template = prompts.get_prompt_template(language)

            # Call LLM with prompt
            ims_query = self.llm_client.parse_query(query, language, prompt_template)

            # Clean up LLM response (remove extra whitespace, newlines)
            ims_query = ' '.join(ims_query.split())

            logger.info(f"LLM parsed: '{query}' -> '{ims_query}' (lang={language})")

            return ParseResult(
                ims_query=ims_query,
                confidence=0.8,  # LLM confidence (conservative)
                method='llm',
                language=language,
                explanation="Parsed using LLM fallback for complex query"
            )
        except Exception as e:
            raise LLMError(f"LLM parsing failed: {e}")
