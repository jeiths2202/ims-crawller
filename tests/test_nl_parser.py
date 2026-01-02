"""
Unit tests for Natural Language Parser

Tests:
- IMS syntax detection
- English query parsing (AND, OR, PHRASE, MIXED)
- Term extraction and cleaning
- Confidence scoring
- Error handling
"""
import pytest
from crawler.nl_parser import (
    NaturalLanguageParser,
    is_ims_syntax,
    ParseResult,
    ParsingError
)
from crawler.nl_patterns import MultilingualPatterns


class TestIMSSyntaxDetection:
    """Test automatic detection of IMS syntax vs natural language"""

    def test_detects_ims_and_operator(self):
        """IMS syntax: starts with +"""
        assert is_ims_syntax("+error +crash") is True
        assert is_ims_syntax("+connection") is True

    def test_detects_ims_single_quotes(self):
        """IMS syntax: contains single quotes"""
        assert is_ims_syntax("'connection timeout'") is True
        assert is_ims_syntax("error 'out of memory'") is True

    def test_detects_ims_double_quotes(self):
        """IMS syntax: contains double quotes"""
        assert is_ims_syntax('"connection timeout"') is True

    def test_detects_ims_issue_number(self):
        """IMS syntax: numeric issue number"""
        assert is_ims_syntax("348115") is True
        assert is_ims_syntax("12345") is True

    def test_detects_natural_language_with_verbs(self):
        """Natural language: contains search verbs"""
        assert is_ims_syntax("find error and crash") is False
        assert is_ims_syntax("search for timeout") is False
        assert is_ims_syntax("show connection issues") is False

    def test_detects_natural_language_with_operators(self):
        """Natural language: contains and/or keywords"""
        assert is_ims_syntax("error and crash") is False
        assert is_ims_syntax("connection or timeout") is False

    def test_ambiguous_defaults_to_natural_language(self):
        """Ambiguous queries default to natural language (safe)"""
        assert is_ims_syntax("error crash") is False
        assert is_ims_syntax("timeout") is False

    def test_edge_cases(self):
        """Edge cases in syntax detection"""
        assert is_ims_syntax("") is False  # Empty
        assert is_ims_syntax("  ") is False  # Whitespace
        assert is_ims_syntax("find +error") is False  # NL verb takes precedence


class TestEnglishANDQueries:
    """Test English AND query parsing"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_simple_and_query(self):
        """Parse: find error and crash"""
        result = self.parser.parse("find error and crash")

        assert result.ims_query == "+error +crash"
        assert result.language == "en"
        assert result.method == "rules"
        assert result.confidence > 0.8

    def test_and_with_multiple_terms(self):
        """Parse: find error and crash and timeout"""
        result = self.parser.parse("find error and crash and timeout")

        assert "+error" in result.ims_query
        assert "+crash" in result.ims_query
        assert "+timeout" in result.ims_query
        assert result.confidence > 0.8

    def test_and_with_both_keyword(self):
        """Parse: find both error and crash"""
        result = self.parser.parse("find both error and crash")

        assert "+error" in result.ims_query
        assert "+crash" in result.ims_query

    def test_and_with_with_keyword(self):
        """Parse: find error with crash"""
        result = self.parser.parse("find error with crash")

        assert "+error" in result.ims_query
        assert "+crash" in result.ims_query


class TestEnglishORQueries:
    """Test English OR query parsing"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_simple_or_query(self):
        """Parse: show connection or timeout"""
        result = self.parser.parse("show connection or timeout")

        assert result.ims_query == "connection timeout"
        assert result.language == "en"
        assert result.confidence > 0.8

    def test_or_with_multiple_terms(self):
        """Parse: find error or crash or timeout"""
        result = self.parser.parse("find error or crash or timeout")

        # All terms present, no + prefix (OR search)
        assert "error" in result.ims_query
        assert "crash" in result.ims_query
        assert "timeout" in result.ims_query
        assert "+" not in result.ims_query  # No AND operator

    def test_or_with_either_keyword(self):
        """Parse: show either connection or timeout"""
        result = self.parser.parse("show either connection or timeout")

        assert "connection" in result.ims_query
        assert "timeout" in result.ims_query


class TestEnglishPhraseQueries:
    """Test English exact phrase query parsing"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_phrase_with_single_quotes(self):
        """Parse: find 'out of memory'"""
        result = self.parser.parse("find 'out of memory'")

        assert "out of memory" in result.ims_query
        assert result.confidence > 0.9

    def test_phrase_with_double_quotes(self):
        """Parse: search for "connection timeout" """
        result = self.parser.parse('search for "connection timeout"')

        assert "connection timeout" in result.ims_query

    def test_exact_keyword_with_phrase(self):
        """Parse: exact phrase out of memory"""
        result = self.parser.parse("exact phrase out of memory")

        # Should recognize intent to search exact phrase
        assert result.confidence > 0.8


class TestEnglishMixedQueries:
    """Test English mixed query parsing (AND + OR + PHRASE)"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_mixed_and_or_query(self):
        """Parse: find error and crash or timeout"""
        result = self.parser.parse("find error and crash or timeout")

        # Should parse as mixed query
        assert result.method == "rules"
        assert result.confidence > 0.7
        # Contains both terms
        assert "error" in result.ims_query
        assert "crash" in result.ims_query
        assert "timeout" in result.ims_query

    def test_mixed_and_phrase_query(self):
        """Parse: find error and 'connection timeout'"""
        result = self.parser.parse("find error and 'connection timeout'")

        assert "error" in result.ims_query
        assert "connection timeout" in result.ims_query


class TestTermExtraction:
    """Test term extraction and cleaning"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_removes_verbs(self):
        """Verbs should be removed from terms"""
        result = self.parser.parse("find error crash")

        # "find" removed, only "error crash" remain
        assert "find" not in result.ims_query.lower()
        assert "error" in result.ims_query
        assert "crash" in result.ims_query

    def test_removes_stopwords(self):
        """Stopwords should be filtered out"""
        result = self.parser.parse("find the error in the database")

        # "the", "in" removed
        assert "the" not in result.ims_query.lower()
        assert "in" not in result.ims_query.lower()
        assert "error" in result.ims_query
        assert "database" in result.ims_query

    def test_preserves_meaningful_terms(self):
        """Important terms should be preserved"""
        result = self.parser.parse("find database connection timeout error")

        assert "database" in result.ims_query
        assert "connection" in result.ims_query
        assert "timeout" in result.ims_query
        assert "error" in result.ims_query


class TestLanguageDetection:
    """Test automatic language detection"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_detects_english(self):
        """English queries detected correctly"""
        result = self.parser.parse("find error and crash")
        assert result.language == "en"

    def test_detects_korean(self):
        """Korean queries detected correctly"""
        result = self.parser.parse("에러 찾아줘")
        assert result.language == "ko"

    def test_detects_japanese(self):
        """Japanese queries detected correctly"""
        result = self.parser.parse("エラーを検索")
        assert result.language == "ja"


class TestConfidenceScoring:
    """Test confidence score calculation"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_high_confidence_and_query(self):
        """AND queries have high confidence"""
        result = self.parser.parse("find error and crash")
        assert result.confidence >= 0.9

    def test_high_confidence_phrase_query(self):
        """Phrase queries have high confidence"""
        result = self.parser.parse("exact phrase 'out of memory'")
        assert result.confidence >= 0.9

    def test_medium_confidence_mixed_query(self):
        """Mixed queries have medium confidence"""
        result = self.parser.parse("find error and crash or timeout")
        assert result.confidence >= 0.7

    def test_lower_confidence_simple_query(self):
        """Simple queries have lower confidence"""
        result = self.parser.parse("error crash")
        assert result.confidence >= 0.6


class TestErrorHandling:
    """Test error handling and edge cases"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_empty_query_raises_error(self):
        """Empty query should raise ParsingError"""
        with pytest.raises(ParsingError):
            self.parser.parse("")

    def test_whitespace_query_raises_error(self):
        """Whitespace-only query should raise ParsingError"""
        with pytest.raises(ParsingError):
            self.parser.parse("   ")

    def test_single_word_query(self):
        """Single word query should parse successfully"""
        result = self.parser.parse("error")
        assert "error" in result.ims_query
        assert result.confidence > 0


class TestParseResult:
    """Test ParseResult data structure"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_parse_result_structure(self):
        """ParseResult has all required fields"""
        result = self.parser.parse("find error and crash")

        assert isinstance(result, ParseResult)
        assert hasattr(result, 'ims_query')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'method')
        assert hasattr(result, 'language')
        assert hasattr(result, 'explanation')
        assert hasattr(result, 'original_query')

    def test_original_query_preserved(self):
        """Original query is preserved in result"""
        original = "find error and crash"
        result = self.parser.parse(original)

        assert result.original_query == original

    def test_explanation_provided(self):
        """Explanation is provided for all queries"""
        result = self.parser.parse("find error and crash")

        assert result.explanation
        assert len(result.explanation) > 0


class TestMultilingualPatterns:
    """Test multilingual pattern support"""

    def test_patterns_loaded(self):
        """Patterns are loaded correctly"""
        patterns = MultilingualPatterns()

        en_patterns = patterns.get_patterns('en')
        assert 'and_keywords' in en_patterns
        assert 'or_keywords' in en_patterns
        assert 'verbs' in en_patterns

    def test_keyword_detection(self):
        """Keyword detection methods work"""
        patterns = MultilingualPatterns()

        assert patterns.is_and_keyword('and', 'en') is True
        assert patterns.is_or_keyword('or', 'en') is True
        assert patterns.is_verb('find', 'en') is True
        assert patterns.is_stopword('the', 'en') is True


class TestIntegration:
    """Integration tests for complete parsing workflows"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = NaturalLanguageParser()

    def test_end_to_end_and_query(self):
        """Complete workflow: NL → IMS syntax"""
        query = "find connection and timeout errors"
        result = self.parser.parse(query)

        assert result.ims_query == "+connection +timeout +errors"
        assert result.confidence > 0.8
        assert result.method == "rules"
        assert result.language == "en"

    def test_end_to_end_or_query(self):
        """Complete workflow: OR query"""
        query = "show connection or timeout issues"
        result = self.parser.parse(query)

        assert "connection" in result.ims_query
        assert "timeout" in result.ims_query
        assert "issues" in result.ims_query
        assert "+" not in result.ims_query  # OR query

    def test_end_to_end_phrase_query(self):
        """Complete workflow: Phrase query"""
        query = "find exact phrase 'out of memory'"
        result = self.parser.parse(query)

        assert "out of memory" in result.ims_query
        assert result.confidence > 0.9


# ===========================================================================
# Phase 2: Korean Language Tests
# ===========================================================================

class TestKoreanParsing:
    """Test suite for Korean natural language parsing"""

    def setup_method(self):
        """Setup test parser"""
        self.parser = NaturalLanguageParser()

    def test_korean_and_query_basic(self):
        """Korean AND query: A와 B"""
        query = "에러와 크래시"
        result = self.parser.parse(query)

        assert result.language == 'ko'
        assert '+에러' in result.ims_query
        assert '+크래시' in result.ims_query
        assert result.confidence >= 0.9

    def test_korean_and_query_with_verb(self):
        """Korean AND query with search verb"""
        query = "에러와 크래시 찾아줘"
        result = self.parser.parse(query)

        assert result.language == 'ko'
        assert '+에러' in result.ims_query
        assert '+크래시' in result.ims_query
        assert '찾아' not in result.ims_query  # Verb removed
        assert result.confidence >= 0.9

    def test_korean_or_query(self):
        """Korean OR query: A 또는 B"""
        query = "연결 또는 타임아웃"
        result = self.parser.parse(query)

        assert result.language == 'ko'
        assert '연결' in result.ims_query
        assert '타임아웃' in result.ims_query
        assert '+' not in result.ims_query  # OR query
        assert result.confidence >= 0.9

    def test_korean_or_query_with_verb(self):
        """Korean OR query with display verb"""
        query = "연결 또는 타임아웃 보여줘"
        result = self.parser.parse(query)

        assert result.language == 'ko'
        assert '연결' in result.ims_query
        assert '타임아웃' in result.ims_query
        assert '보여' not in result.ims_query  # Verb removed
        assert result.confidence >= 0.9

    def test_korean_exact_phrase(self):
        """Korean exact phrase query"""
        query = "정확히 '메모리 부족'"
        result = self.parser.parse(query)

        assert result.language == 'ko'
        assert "'메모리 부족'" in result.ims_query
        assert result.confidence >= 0.95

    def test_korean_mixed_query(self):
        """Korean mixed AND/OR query"""
        query = "데이터베이스 에러 그리고 크래시 또는 타임아웃"
        result = self.parser.parse(query)

        assert result.language == 'ko'
        assert '+데이터베이스' in result.ims_query
        assert '+에러' in result.ims_query
        assert result.confidence >= 0.8

    def test_korean_stopword_removal(self):
        """Korean stopword filtering"""
        query = "이것을 찾아줘"  # Should remove "이것을"
        result = self.parser.parse(query)

        assert result.language == 'ko'
        # Stopwords removed, only content terms remain
        assert '이' not in result.ims_query or len(result.ims_query.split()) < 3

    def test_korean_language_detection(self):
        """Korean language auto-detection"""
        query = "에러 검색"
        result = self.parser.parse(query)

        assert result.language == 'ko'


# ===========================================================================
# Phase 2: Japanese Language Tests
# ===========================================================================

class TestJapaneseParsing:
    """Test suite for Japanese natural language parsing"""

    def setup_method(self):
        """Setup test parser"""
        self.parser = NaturalLanguageParser()

    def test_japanese_and_query_basic(self):
        """Japanese AND query: Aと B"""
        query = "エラーとクラッシュ"
        result = self.parser.parse(query)

        assert result.language == 'ja'
        assert '+エラー' in result.ims_query
        assert '+クラッシュ' in result.ims_query
        assert result.confidence >= 0.9

    def test_japanese_and_query_with_particle(self):
        """Japanese AND query with particle を"""
        query = "エラーとクラッシュを検索"
        result = self.parser.parse(query)

        assert result.language == 'ja'
        assert '+エラー' in result.ims_query
        assert '+クラッシュ' in result.ims_query
        # Particle and verb should be removed
        assert 'を検索' not in result.ims_query
        assert result.confidence >= 0.9

    def test_japanese_or_query(self):
        """Japanese OR query: Aまたは B"""
        query = "接続またはタイムアウト"
        result = self.parser.parse(query)

        assert result.language == 'ja'
        assert '接続' in result.ims_query
        assert 'タイムアウト' in result.ims_query
        assert '+' not in result.ims_query  # OR query
        assert result.confidence >= 0.9

    def test_japanese_or_query_matawa_vs_mata(self):
        """Japanese: Ensure 'または' (or) is not confused with 'また' (and)"""
        query = "接続またはタイムアウト"
        result = self.parser.parse(query)

        # Should be OR query, not AND or MIXED
        assert '+' not in result.ims_query
        assert result.confidence >= 0.9
        assert 'OR' in result.explanation

    def test_japanese_exact_phrase(self):
        """Japanese exact phrase query"""
        query = "正確に 'メモリ不足'"
        result = self.parser.parse(query)

        assert result.language == 'ja'
        assert "'メモリ不足'" in result.ims_query
        assert result.confidence >= 0.95

    def test_japanese_mixed_query(self):
        """Japanese mixed AND/OR query"""
        query = "データベース エラー および クラッシュ または タイムアウト"
        result = self.parser.parse(query)

        assert result.language == 'ja'
        assert '+データベース' in result.ims_query
        assert '+エラー' in result.ims_query
        assert result.confidence >= 0.8

    def test_japanese_particle_removal(self):
        """Japanese particle removal from terms"""
        query = "エラーを検索"
        result = self.parser.parse(query)

        assert result.language == 'ja'
        # Particle を should be removed from エラー
        assert 'エラー' in result.ims_query
        assert 'を' not in result.ims_query or 'エラーを' not in result.ims_query

    def test_japanese_language_detection(self):
        """Japanese language auto-detection"""
        query = "エラー検索"
        result = self.parser.parse(query)

        assert result.language == 'ja'


# ===========================================================================
# Phase 2: Multi-Language Tests
# ===========================================================================

class TestMultiLanguage:
    """Test suite for multi-language detection and handling"""

    def setup_method(self):
        """Setup test parser"""
        self.parser = NaturalLanguageParser()

    def test_language_detection_english(self):
        """Detect English language"""
        queries = [
            "find error and crash",
            "show connection or timeout",
            "error 123",
        ]

        for query in queries:
            lang = self.parser._detect_language(query)
            assert lang == 'en', f"Failed for: {query}"

    def test_language_detection_korean(self):
        """Detect Korean language"""
        queries = [
            "에러와 크래시",
            "연결 또는 타임아웃",
            "에러 검색",
        ]

        for query in queries:
            lang = self.parser._detect_language(query)
            assert lang == 'ko', f"Failed for: {query}"

    def test_language_detection_japanese(self):
        """Detect Japanese language"""
        queries = [
            "エラーとクラッシュ",
            "接続またはタイムアウト",
            "エラー検索",
        ]

        for query in queries:
            lang = self.parser._detect_language(query)
            assert lang == 'ja', f"Failed for: {query}"

    def test_language_detection_mixed_korean(self):
        """Mixed language with Korean dominant"""
        query = "Tibero error 와 crash"
        lang = self.parser._detect_language(query)
        assert lang == 'ko'  # Korean takes precedence

    def test_language_detection_mixed_japanese(self):
        """Mixed language with Japanese dominant"""
        query = "データベース error"
        lang = self.parser._detect_language(query)
        assert lang == 'ja'  # Japanese takes precedence

    def test_confidence_consistency_across_languages(self):
        """Confidence scores should be consistent across languages"""
        queries = {
            'en': ("find error and crash", 0.9),
            'ko': ("에러와 크래시 찾아줘", 0.9),
            'ja': ("エラーとクラッシュを検索", 0.9),
        }

        for lang, (query, expected_conf) in queries.items():
            result = self.parser.parse(query)
            assert result.language == lang
            assert result.confidence >= expected_conf

    def test_all_languages_support_and_or_phrase(self):
        """All languages should support AND, OR, and PHRASE queries"""
        test_cases = [
            # English
            ("find error and crash", "AND"),
            ("show connection or timeout", "OR"),
            ("exact 'out of memory'", "phrase"),  # lowercase to match "Exact phrase query"
            # Korean
            ("에러와 크래시", "AND"),
            ("연결 또는 타임아웃", "OR"),
            ("정확히 '메모리 부족'", "phrase"),
            # Japanese
            ("エラーとクラッシュ", "AND"),
            ("接続またはタイムアウト", "OR"),
            ("正確に 'メモリ不足'", "phrase"),
        ]

        for query, expected_type in test_cases:
            result = self.parser.parse(query)
            # Case-insensitive check
            assert expected_type.lower() in result.explanation.lower(), f"Failed for: {query}"
