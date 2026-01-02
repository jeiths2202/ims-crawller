"""
Multilingual Natural Language Patterns for IMS Query Parsing

This module defines pattern dictionaries for detecting natural language
keywords and operators in English, Korean, and Japanese queries.
"""
import re
from typing import Dict, List, Any


class MultilingualPatterns:
    """
    Pattern definitions for multilingual natural language parsing

    Supports:
    - English (en)
    - Korean (ko) - Phase 2
    - Japanese (ja) - Phase 2
    """

    PATTERNS: Dict[str, Dict[str, Any]] = {
        'en': {
            # AND operation keywords
            'and_keywords': ['and', 'with', 'plus', 'both', 'also'],

            # OR operation keywords
            'or_keywords': ['or', 'either'],

            # Exact phrase keywords
            'exact_keywords': ['exact', 'exactly', 'phrase', 'literal', 'literally'],

            # Common verbs that indicate search intent
            'verbs': ['find', 'search', 'show', 'list', 'get', 'display', 'fetch', 'retrieve'],

            # Product extraction patterns (regex)
            'product_patterns': [
                r'in\s+(\w+)',           # "in OpenFrame"
                r'for\s+(\w+)',          # "for Tibero"
                r'about\s+(\w+)',        # "about JEUS"
                r'regarding\s+(\w+)',    # "regarding OpenFrame"
            ],

            # Stopwords to remove (common words that don't affect search)
            'stopwords': [
                'the', 'a', 'an', 'is', 'are', 'was', 'were',
                'be', 'been', 'being', 'have', 'has', 'had',
                'do', 'does', 'did', 'will', 'would', 'should',
                'could', 'may', 'might', 'must', 'can',
                'this', 'that', 'these', 'those',
                'i', 'you', 'he', 'she', 'it', 'we', 'they',
                'me', 'him', 'her', 'us', 'them',
                'my', 'your', 'his', 'its', 'our', 'their',
                'all', 'some', 'any', 'many', 'much', 'more', 'most',
                'in', 'on', 'at', 'to', 'from', 'of', 'by', 'for', 'about',
            ]
        },

        # Korean patterns (Phase 2)
        'ko': {
            # AND operation keywords
            'and_keywords': ['와', '과', '그리고', '및', '또한', '하고', '랑', '이랑'],

            # OR operation keywords
            'or_keywords': ['또는', '혹은', '이나', '나', '거나'],

            # Exact phrase keywords
            'exact_keywords': ['정확히', '정확한', '완전히', '정확하게', '그대로'],

            # Common verbs that indicate search intent
            'verbs': ['찾아', '검색', '보여', '알려', '가져와', '찾기', '검색해', '보여줘', '알려줘'],

            # Product extraction patterns (regex)
            'product_patterns': [
                r'([가-힣A-Za-z0-9]+)에서',        # "OpenFrame에서"
                r'([가-힣A-Za-z0-9]+)의',          # "Tibero의"
                r'([가-힣A-Za-z0-9]+)관련',        # "JEUS관련"
                r'([가-힣A-Za-z0-9]+)에',          # "Tibero에"
                r'([가-힣A-Za-z0-9]+)로',          # "JEUS로"
            ],

            # Stopwords to remove (common Korean particles and auxiliary words)
            'stopwords': [
                '이', '그', '저', '것', '수', '등', '들', '좀', '더', '를', '을',
                '가', '이가', '에', '에서', '으로', '로', '의', '도', '만', '까지',
                '부터', '조차', '마저', '은', '는', '이는', '있는', '없는', '되는',
                '하는', '한', '할', '해', '줘', '주세요', '요', '입니다', '습니다'
            ]
        },

        # Japanese patterns (Phase 2)
        'ja': {
            # AND operation keywords
            'and_keywords': ['と', 'および', 'かつ', 'そして', 'さらに', 'また'],

            # OR operation keywords
            'or_keywords': ['または', 'か', 'あるいは', 'もしくは', 'ないし'],

            # Exact phrase keywords
            'exact_keywords': ['正確に', '完全一致', '完全に', 'そのまま', '厳密に'],

            # Common verbs that indicate search intent
            'verbs': ['検索', '探す', '見つけ', '表示', '取得', '調べる', '検索する', '見つける'],

            # Product extraction patterns (regex)
            'product_patterns': [
                r'([ぁ-んァ-ヶー一-龯A-Za-z0-9]+)で',              # "OpenFrameで"
                r'([ぁ-んァ-ヶー一-龯A-Za-z0-9]+)の',              # "Tiberoの"
                r'([ぁ-んァ-ヶー一-龯A-Za-z0-9]+)に関する',        # "JEUSに関する"
                r'([ぁ-んァ-ヶー一-龯A-Za-z0-9]+)について',        # "Tiberoについて"
                r'([ぁ-んァ-ヶー一-龯A-Za-z0-9]+)における',        # "JEUSにおける"
            ],

            # Stopwords to remove (common Japanese particles and auxiliary words)
            'stopwords': [
                'の', 'が', 'を', 'に', 'は', 'で', 'と', 'や', 'から', 'まで',
                'より', 'へ', 'も', 'か', 'な', 'ね', 'よ', 'だ', 'です', 'ます',
                'である', 'する', 'した', 'される', 'されている', 'ある', 'いる',
                'この', 'その', 'あの', 'どの', 'これ', 'それ', 'あれ', 'どれ'
            ],

            # Japanese particles that often attach to words (for post-processing)
            'particles': ['を', 'に', 'は', 'が', 'で', 'と', 'や', 'から', 'まで', 'より', 'へ', 'も']
        }
    }

    def __init__(self):
        """Initialize pattern matcher"""
        self._compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency"""
        for lang, patterns in self.PATTERNS.items():
            self._compiled_patterns[lang] = {
                'product': [re.compile(p, re.IGNORECASE) for p in patterns.get('product_patterns', [])]
            }

    def get_patterns(self, language: str = 'en') -> Dict[str, Any]:
        """
        Get patterns for specified language

        Args:
            language: Language code ('en', 'ko', 'ja')

        Returns:
            Dictionary of patterns for the language
        """
        return self.PATTERNS.get(language, self.PATTERNS['en'])

    def get_compiled_patterns(self, language: str = 'en') -> Dict[str, List[re.Pattern]]:
        """
        Get compiled regex patterns for specified language

        Args:
            language: Language code ('en', 'ko', 'ja')

        Returns:
            Dictionary of compiled regex patterns
        """
        return self._compiled_patterns.get(language, self._compiled_patterns['en'])

    def is_and_keyword(self, word: str, language: str = 'en') -> bool:
        """Check if word is an AND operator keyword"""
        patterns = self.get_patterns(language)
        return word.lower() in patterns['and_keywords']

    def is_or_keyword(self, word: str, language: str = 'en') -> bool:
        """Check if word is an OR operator keyword"""
        patterns = self.get_patterns(language)
        return word.lower() in patterns['or_keywords']

    def is_exact_keyword(self, word: str, language: str = 'en') -> bool:
        """Check if word indicates exact phrase search"""
        patterns = self.get_patterns(language)
        return word.lower() in patterns['exact_keywords']

    def is_verb(self, word: str, language: str = 'en') -> bool:
        """Check if word is a search intent verb"""
        patterns = self.get_patterns(language)
        return word.lower() in patterns['verbs']

    def is_stopword(self, word: str, language: str = 'en') -> bool:
        """Check if word is a stopword (should be filtered out)"""
        patterns = self.get_patterns(language)
        return word.lower() in patterns.get('stopwords', [])

    def extract_product(self, query: str, language: str = 'en') -> str:
        """
        Extract product name from query using patterns

        Args:
            query: Natural language query
            language: Language code

        Returns:
            Product name if found, empty string otherwise
        """
        compiled = self.get_compiled_patterns(language)

        for pattern in compiled['product']:
            match = pattern.search(query)
            if match:
                return match.group(1)

        return ''
