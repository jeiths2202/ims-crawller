"""
Ollama LLM Client for Natural Language Query Parsing and Report Enhancement

Provides local LLM fallback for:
1. Complex queries with confidence < 0.7 (query parsing)
2. Report generation enhancement (issue analysis)
"""
import logging
import requests
from typing import Optional, Dict
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

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate text using Ollama LLM (general purpose)

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            LLMError: If LLM generation fails
        """
        if not self.available:
            raise LLMError("Ollama server not available")

        try:
            # Build request payload
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            # Make request
            logger.info(f"Generating with {self.config.model}...")
            response = requests.post(
                f"{self.config.base_url}/api/generate",
                json=payload,
                timeout=self.config.timeout * 3  # Longer timeout for report generation
            )

            response.raise_for_status()

            # Parse response
            result = response.json()
            generated_text = result.get('response', '').strip()

            logger.info(f"Generated {len(generated_text)} characters")
            return generated_text

        except requests.exceptions.Timeout:
            raise LLMError(f"LLM generation timeout after {self.config.timeout * 3}s")
        except requests.exceptions.RequestException as e:
            raise LLMError(f"LLM generation failed: {e}")

    def analyze_issue(
        self,
        title: str,
        description: str,
        comments: Optional[list] = None,
        language: str = "ko"
    ) -> Dict[str, str]:
        """
        Analyze issue and provide structured insights for reports

        Args:
            title: Issue title
            description: Issue description
            comments: Optional list of comments
            language: Output language (ko, ja, en)

        Returns:
            Dictionary with analysis sections

        Raises:
            LLMError: If analysis fails
        """
        if not self.available:
            raise LLMError("LLM not available for issue analysis")

        # Build prompt based on language
        if language == "ko":
            system_prompt = """당신은 기술 이슈 분석 전문가입니다.
이슈를 분석하여 다음을 제공하세요:
1. 기술적 근본 원인
2. 영향 분석
3. 해결 방안
4. 예상 타임라인

간결하고 명확하게 작성하세요."""

            prompt = f"""다음 이슈를 분석하세요:

제목: {title}

설명: {description[:1000]}

"""
            if comments:
                prompt += "\n주요 코멘트:\n"
                for comment in comments[:3]:
                    prompt += f"- {comment.get('content', '')[:200]}\n"

        else:  # English
            system_prompt = """You are a technical issue analysis expert.
Analyze the issue and provide:
1. Technical root cause
2. Impact analysis
3. Solution approach
4. Timeline estimation

Be concise and clear."""

            prompt = f"""Analyze this issue:

Title: {title}

Description: {description[:1000]}

"""
            if comments:
                prompt += "\nKey comments:\n"
                for comment in comments[:3]:
                    prompt += f"- {comment.get('content', '')[:200]}\n"

        try:
            # Generate analysis
            analysis_text = self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=800
            )

            # Parse structured output
            sections = {
                'root_cause': '',
                'impact': '',
                'solution': '',
                'timeline': ''
            }

            # Simple section extraction
            lines = analysis_text.split('\n')
            current_section = 'root_cause'

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detect section headers
                if '원인' in line or 'cause' in line.lower():
                    current_section = 'root_cause'
                elif '영향' in line or 'impact' in line.lower():
                    current_section = 'impact'
                elif '해결' in line or 'solution' in line.lower():
                    current_section = 'solution'
                elif '타임라인' in line or 'timeline' in line.lower():
                    current_section = 'timeline'
                else:
                    sections[current_section] += line + '\n'

            return sections

        except Exception as e:
            logger.error(f"Issue analysis failed: {e}")
            raise LLMError(f"Issue analysis failed: {e}")

    def __repr__(self):
        """String representation"""
        status = "available" if self.available else "unavailable"
        return f"OllamaClient(model={self.config.model}, status={status})"


def get_default_llm_client() -> Optional['OllamaClient']:
    """
    Get default LLM client with automatic model selection

    Returns:
        OllamaClient if available, None otherwise
    """
    # Try models in order of preference (faster models first)
    models = [
        "gemma:2b",      # Fast, efficient
        "phi3:mini",     # Good balance
        "llama2:7b",     # More capable but slower
    ]

    for model in models:
        try:
            config = LLMConfig(model=model)
            client = OllamaClient(config=config)
            if client.available:
                logger.info(f"Using LLM model: {model}")
                return client
        except Exception as e:
            logger.debug(f"Model {model} not available: {e}")

    logger.info("No LLM models available, using template-only mode")
    return None
