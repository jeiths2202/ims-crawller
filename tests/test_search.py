"""
Unit tests for SearchQueryBuilder
"""
import pytest
from crawler.search import SearchQueryBuilder


class TestSearchQueryBuilder:
    """Test cases for IMS search query building"""

    def test_or_search(self):
        """Test OR search with space delimiter"""
        result = SearchQueryBuilder.build_or_query(['Tmax', 'Tibero'])
        assert result == 'Tmax Tibero'

    def test_and_search(self):
        """Test AND search with + operator"""
        result = SearchQueryBuilder.build_and_query(['error', 'timeout'])
        assert result == '+error +timeout'

    def test_exact_phrase(self):
        """Test exact phrase search with quotation marks"""
        result = SearchQueryBuilder.build_exact_phrase('connection timeout')
        assert result == '"connection timeout"'

    def test_exact_phrase_strips_quotes(self):
        """Test that existing quotes are handled correctly"""
        result = SearchQueryBuilder.build_exact_phrase('"already quoted"')
        assert result == '"already quoted"'

    def test_complex_query(self):
        """Test complex query combining OR, AND, and exact phrases"""
        result = SearchQueryBuilder.build_complex_query(
            or_keywords=['Tmax', 'Tibero'],
            and_keywords=['error'],
            exact_phrases=['connection timeout']
        )
        assert 'Tmax Tibero' in result
        assert '+error' in result
        assert '"connection timeout"' in result

    def test_build_query_with_product(self):
        """Test query building with product filter - product handled by UI, not in query"""
        result = SearchQueryBuilder.build_query('error', product='Tibero')
        # Product is now handled by UI dropdown, not in query string
        assert result == 'error'

    def test_build_query_without_product(self):
        """Test query building without product filter"""
        result = SearchQueryBuilder.build_query('error timeout')
        assert result == 'error timeout'

    def test_issue_number_query(self):
        """Test issue number search"""
        result = SearchQueryBuilder.build_issue_number_query('IMS-12345')
        assert result == '+IMS-12345'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
