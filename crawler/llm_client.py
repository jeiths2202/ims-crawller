"""
Ollama LLM Client for Natural Language Query Parsing

Provides local LLM fallback for complex queries with confidence < 0.7
"""
import logging
import requests
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Exception raised when LLM operations fail"""
    pass


@dataclass
class LLMConfig:
    """LLM configuration"""
    model: str = "gemma:2b"
    base_url: str = "http://localhost:11434"
    timeout: int = 10
    temperature: float = 0.1
    max_tokens: int = 50


class OllamaClient:
    """
    Ollama Local LLM Client

    Connects to local Ollama server for natural language query parsing.
    Used as fallback when rule-based parsing has low confidence.

    Requirements:
    - Ollama installed and running locally
    - Model downloaded (default: gemma:2b)

    Installation:
        curl -fsSL https://ollama.com/install.sh | sh
        ollama pull gemma:2b
        ollama serve
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Ollama client

        Args:
            config: LLM configuration (uses defaults if None)
        """
        self.config = config or LLMConfig()
        self.available = self._check_availability()

        if self.available:
            logger.info(f"Ollama client initialized: {self.config.base_url}, model={self.config.model}")
        else:
            logger.warning("Ollama server not available - LLM fallback disabled")

    def _check_availability(self) -> bool:
        """
        Check if Ollama server is running and model is available

        Returns:
            True if server is accessible and model exists
        """
        try:
            # Check server health
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=2
            )

            if response.status_code != 200:
                return False

            # Check if model is available
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]

            # Check for exact match or with :latest tag
            model_available = (
                self.config.model in model_names or
                f"{self.config.model}:latest" in model_names or
                any(self.config.model in name for name in model_names)
            )

            if not model_available:
                logger.warning(
                    f"Model '{self.config.model}' not found. Available: {model_names}\n"
                    f"Run: ollama pull {self.config.model}"
                )
                return False

            return True

        except Exception as e:
            logger.debug(f"Ollama server check failed: {e}")
            return False

    def parse_query(self, nl_query: str, language: str, prompt_template: str) -> str:
        """
        Parse natural language query using LLM

        Args:
            nl_query: Natural language query
            language: Language code ('en', 'ko', 'ja')
            prompt_template: Few-shot prompt template with {query} placeholder

        Returns:
            Parsed IMS syntax query

        Raises:
            LLMError: If LLM parsing fails
        """
        if not self.available:
            raise LLMError("Ollama server not available")

        # Build prompt from template
        prompt = prompt_template.format(query=nl_query)

        try:
            # Call Ollama API
            response = requests.post(
                f"{self.config.base_url}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens,
                    }
                },
                timeout=self.config.timeout
            )

            response.raise_for_status()

            # Extract response
            result = response.json()
            parsed_query = result.get('response', '').strip()

            if not parsed_query:
                raise LLMError("LLM returned empty response")

            logger.info(f"LLM parsed '{nl_query}' -> '{parsed_query}' (lang={language})")

            return parsed_query

        except requests.exceptions.Timeout:
            raise LLMError(f"LLM request timeout after {self.config.timeout}s")
        except requests.exceptions.RequestException as e:
            raise LLMError(f"LLM request failed: {e}")
        except Exception as e:
            raise LLMError(f"Unexpected LLM error: {e}")

    def __repr__(self):
        """String representation"""
        status = "available" if self.available else "unavailable"
        return f"OllamaClient(model={self.config.model}, status={status})"
