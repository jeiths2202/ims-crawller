"""
Tests for LLM Integration (Phase 3)

Tests LLM client and integration with NaturalLanguageParser
"""
import pytest
from unittest.mock import Mock, patch

from crawler.llm_client import OllamaClient, LLMConfig, LLMError
from crawler.nl_parser import NaturalLanguageParser, ParseResult
from crawler import prompts


class TestLLMConfig:
    """Test LLM configuration"""

    def test_default_config(self):
        """Default configuration uses gemma:2b"""
        config = LLMConfig()

        assert config.model == "gemma:2b"
        assert config.base_url == "http://localhost:11434"
        assert config.timeout == 10
        assert config.temperature == 0.1
        assert config.max_tokens == 50

    def test_custom_config(self):
        """Custom configuration"""
        config = LLMConfig(
            model="llama3:8b",
            base_url="http://192.168.1.100:11434",
            timeout=30,
            temperature=0.5,
            max_tokens=100
        )

        assert config.model == "llama3:8b"
        assert config.base_url == "http://192.168.1.100:11434"
        assert config.timeout == 30
        assert config.temperature == 0.5
        assert config.max_tokens == 100


class TestOllamaClient:
    """Test Ollama client"""

    @patch('requests.get')
    def test_client_initialization_server_unavailable(self, mock_get):
        """Client gracefully handles server unavailable"""
        mock_get.side_effect = Exception("Connection refused")

        client = OllamaClient()

        assert client.available == False
        assert "gemma:2b" in str(client)
        assert "unavailable" in str(client)

    @patch('requests.get')
    def test_client_initialization_model_not_found(self, mock_get):
        """Client detects when model is not downloaded"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [
                {'name': 'llama3:8b'},
                {'name': 'phi3:mini'}
            ]
        }

        client = OllamaClient()

        # gemma:2b not in list, should be unavailable
        assert client.available == False

    @patch('requests.get')
    def test_client_initialization_success(self, mock_get):
        """Client successfully initializes when server and model available"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [
                {'name': 'gemma:2b'},
                {'name': 'llama3:8b'}
            ]
        }

        client = OllamaClient()

        assert client.available == True
        assert "available" in str(client)

    @patch('requests.post')
    @patch('requests.get')
    def test_parse_query_success(self, mock_get, mock_post):
        """LLM successfully parses query"""
        # Setup client as available
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'gemma:2b'}]
        }

        # Setup LLM response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': '+error +crash'
        }

        client = OllamaClient()
        prompt = prompts.get_prompt_template('en')

        result = client.parse_query("find error and crash", 'en', prompt)

        assert result == '+error +crash'
        assert mock_post.called

    def test_parse_query_client_unavailable(self):
        """Raises error when client unavailable"""
        client = OllamaClient()
        client.available = False

        with pytest.raises(LLMError, match="not available"):
            client.parse_query("test query", 'en', "test prompt")


class TestPrompts:
    """Test few-shot prompts"""

    def test_english_prompt(self):
        """English prompt template"""
        template = prompts.get_prompt_template('en')

        assert '{query}' in template
        assert 'IMS Syntax' in template
        assert '+error +crash' in template  # Few-shot example

    def test_korean_prompt(self):
        """Korean prompt template"""
        template = prompts.get_prompt_template('ko')

        assert '{query}' in template
        assert 'IMS' in template
        assert '+에러 +크래시' in template  # Few-shot example

    def test_japanese_prompt(self):
        """Japanese prompt template"""
        template = prompts.get_prompt_template('ja')

        assert '{query}' in template
        assert 'IMS' in template
        assert '+エラー +クラッシュ' in template  # Few-shot example

    def test_build_prompt(self):
        """Build complete prompt with query"""
        prompt = prompts.build_prompt("find error and crash", 'en')

        assert 'find error and crash' in prompt
        assert 'IMS Syntax' in prompt


class TestNLParserLLMIntegration:
    """Test NL parser with LLM integration"""

    def test_parser_without_llm(self):
        """Parser works without LLM client"""
        parser = NaturalLanguageParser(llm_client=None)

        result = parser.parse("find error and crash")

        assert result.ims_query == "+error +crash"
        assert result.method == "rules"  # Not LLM
        assert result.confidence >= 0.9

    @patch('requests.get')
    def test_parser_with_llm_high_confidence_uses_rules(self, mock_get):
        """Parser uses rules for high confidence queries (doesn't need LLM)"""
        # Setup available LLM
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'gemma:2b'}]
        }

        llm_client = OllamaClient()
        parser = NaturalLanguageParser(llm_client=llm_client)

        # Simple query - high confidence with rules
        result = parser.parse("find error and crash")

        assert result.ims_query == "+error +crash"
        assert result.method == "rules"  # Used rules, not LLM
        assert result.confidence >= 0.9

    @patch('requests.post')
    @patch('requests.get')
    def test_parser_with_llm_low_confidence_uses_llm(self, mock_get, mock_post):
        """Parser falls back to LLM for low confidence queries"""
        # Setup available LLM
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'gemma:2b'}]
        }

        # Setup LLM response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': '+complex +parsed +query'
        }

        llm_client = OllamaClient()
        parser = NaturalLanguageParser(llm_client=llm_client)

        # Create mock result with low confidence to trigger LLM
        with patch.object(parser, '_parse_with_rules') as mock_rules:
            mock_rules.return_value = ParseResult(
                ims_query="temp",
                confidence=0.6,  # Below 0.7 threshold
                method='rules',
                language='en',
                explanation="Low confidence"
            )

            result = parser.parse("very complex ambiguous query")

            assert result.method == "llm"  # Used LLM fallback
            assert result.confidence == 0.8  # LLM confidence
            assert result.ims_query == '+complex +parsed +query'

    @patch('requests.get')
    def test_parser_llm_fallback_graceful_degradation(self, mock_get):
        """Parser gracefully degrades if LLM fails"""
        # Setup available LLM
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'gemma:2b'}]
        }

        llm_client = OllamaClient()
        parser = NaturalLanguageParser(llm_client=llm_client)

        # Simulate LLM failure
        with patch.object(llm_client, 'parse_query', side_effect=Exception("LLM timeout")):
            # Create low confidence query that would normally trigger LLM
            with patch.object(parser, '_parse_with_rules') as mock_rules:
                rules_result = ParseResult(
                    ims_query="fallback query",
                    confidence=0.6,
                    method='rules',
                    language='en',
                    explanation="Fallback"
                )
                mock_rules.return_value = rules_result

                result = parser.parse("complex query")

                # Should fallback to rules result when LLM fails
                assert result.ims_query == "fallback query"
                assert result.method == "rules"  # Fell back to rules
