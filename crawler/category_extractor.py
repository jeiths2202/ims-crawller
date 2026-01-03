"""
Category extraction for technical issues
Extracts symptom, cause, and solution information using hybrid approach
"""
import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class CategoryExtractor:
    """Extract issue categories using keyword patterns and optional LLM refinement"""

    def __init__(self, llm_client=None):
        """
        Initialize category extractor

        Args:
            llm_client: Optional LLM client for refinement
        """
        self.llm_client = llm_client

        # Multilingual keyword patterns (Korean, Japanese, English)
        self.patterns = {
            'symptom': {
                'ko': [
                    r'발생.*?(?:함|했|합니다|하였습니다)',
                    r'에러.*?(?:발생|나타남|표시)',
                    r'현상.*?(?:발생|나타남|확인)',
                    r'문제.*?(?:발생|있음)',
                    r'(?:timeout|TPETIME|TPETIME|타임아웃).*?(?:발생|에러)',
                    r'멈춤.*?(?:현상|상태)',
                    r'(?:느림|지연|속도).*?(?:현상|문제)',
                    r'(?:실패|fail|failed).*?(?:함|했|합니다)',
                    r'(?:안됨|되지 않음|불가)',
                    r'장애.*?(?:발생|상황|상태)',
                ],
                'ja': [
                    r'(?:エラー|障害).*?(?:発生|表示)',
                    r'(?:問題|現象).*?(?:発生|確認)',
                    r'(?:タイムアウト|timeout).*?(?:発生|エラー)',
                    r'(?:遅延|遅い).*?(?:現象|問題)',
                    r'(?:失敗|できない)',
                ],
                'en': [
                    r'(?:error|failure|issue).*?(?:occur|happen|appear)',
                    r'(?:timeout|hang|freeze).*?(?:occur|issue)',
                    r'(?:slow|delay).*?(?:performance|issue)',
                    r'(?:fail|failed|cannot)',
                ]
            },
            'cause': {
                'ko': [
                    r'원인.*?(?:은|는|:|입니다)',
                    r'이유.*?(?:는|:|입니다)',
                    r'(?:때문|인해|으로인해)',
                    r'(?:설정|구성).*?(?:문제|오류|잘못)',
                    r'(?:버전|모듈).*?(?:문제|충돌)',
                    r'(?:메모리|리소스|자원).*?(?:부족|문제)',
                    r'(?:권한|permission).*?(?:문제|없음)',
                    r'(?:코드|로직).*?(?:오류|버그)',
                ],
                'ja': [
                    r'原因.*?(?:は|:|です)',
                    r'理由.*?(?:は|:|です)',
                    r'(?:による|ため|起因)',
                    r'(?:設定|構成).*?(?:問題|エラー)',
                    r'(?:バージョン|モジュール).*?(?:問題|競合)',
                ],
                'en': [
                    r'(?:cause|reason|root cause).*?(?:is|:|was)',
                    r'(?:due to|because of|caused by)',
                    r'(?:configuration|setting).*?(?:issue|error|problem)',
                    r'(?:version|module).*?(?:conflict|issue)',
                    r'(?:memory|resource).*?(?:shortage|issue)',
                ]
            },
            'solution': {
                'ko': [
                    r'(?:해결|수정|개선).*?(?:방법|방안|함|했)',
                    r'대응.*?(?:방법|방안)',
                    r'조치.*?(?:사항|내용)',
                    r'패치.*?(?:제공|적용|배포)',
                    r'(?:권장|추천).*?(?:사항|방법)',
                    r'(?:변경|수정).*?(?:필요|요청|권장)',
                    r'(?:업데이트|업그레이드)',
                    r'우회.*?(?:방법|방안)',
                ],
                'ja': [
                    r'(?:解決|修正|改善).*?(?:方法|方式)',
                    r'対応.*?(?:方法|方式)',
                    r'パッチ.*?(?:提供|適用)',
                    r'(?:推奨|推薦).*?(?:事項|方法)',
                    r'(?:変更|修正).*?(?:必要|推奨)',
                ],
                'en': [
                    r'(?:solution|fix|resolve|workaround)',
                    r'(?:patch|update|upgrade)',
                    r'(?:recommend|suggest).*?(?:solution|approach)',
                    r'(?:change|modify).*?(?:required|needed)',
                    r'to (?:fix|resolve|address)',
                ]
            }
        }

        # Context window size for extraction
        self.context_window = 200  # characters before and after match

    def extract_with_context(self, text: str, pattern: str, context_size: int = 200) -> List[str]:
        """
        Extract text matching pattern with surrounding context

        Args:
            text: Text to search
            pattern: Regex pattern
            context_size: Characters to include before/after match

        Returns:
            List of matched text snippets with context
        """
        matches = []
        for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            start = max(0, match.start() - context_size)
            end = min(len(text), match.end() + context_size)
            snippet = text[start:end].strip()

            # Clean up snippet
            snippet = re.sub(r'\s+', ' ', snippet)
            if snippet and snippet not in matches:
                matches.append(snippet)

        return matches

    def extract_sentences_by_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """
        Extract sentences containing any of the keywords

        Args:
            text: Text to search
            keywords: List of keywords to look for

        Returns:
            List of sentences containing keywords
        """
        # Split into sentences (simple approach)
        sentences = re.split(r'[.!?\n]+', text)

        matched_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            # Check if any keyword matches
            for keyword in keywords:
                if re.search(keyword, sentence, re.IGNORECASE):
                    if sentence not in matched_sentences:
                        matched_sentences.append(sentence)
                    break

        return matched_sentences

    def extract_categories_keyword(self, issue: Dict) -> Dict[str, List[str]]:
        """
        Extract categories using keyword-based pattern matching

        Args:
            issue: Issue dictionary with title, description, comments

        Returns:
            Dictionary with symptom, cause, solution lists
        """
        # Combine all text content
        text_parts = []

        if issue.get('title'):
            text_parts.append(f"제목: {issue['title']}")

        if issue.get('description'):
            text_parts.append(f"설명: {issue['description']}")

        # Include comments
        comments = issue.get('comments', [])
        if isinstance(comments, list):
            for i, comment in enumerate(comments[:5], 1):  # Limit to first 5 comments
                if isinstance(comment, dict):
                    content = comment.get('content', '')
                elif isinstance(comment, str):
                    content = comment
                else:
                    continue

                if content:
                    text_parts.append(f"댓글{i}: {content}")

        full_text = '\n\n'.join(text_parts)

        # Extract by category
        result = {
            'symptom': [],
            'cause': [],
            'solution': []
        }

        for category in ['symptom', 'cause', 'solution']:
            all_matches = []

            # Try all language patterns
            for lang in ['ko', 'ja', 'en']:
                patterns = self.patterns[category].get(lang, [])

                for pattern in patterns:
                    matches = self.extract_with_context(full_text, pattern, self.context_window)
                    all_matches.extend(matches)

            # Deduplicate and limit
            seen = set()
            unique_matches = []
            for match in all_matches:
                # Use first 100 chars as dedup key
                key = match[:100]
                if key not in seen:
                    seen.add(key)
                    unique_matches.append(match)

            result[category] = unique_matches[:5]  # Limit to top 5 per category

        # Calculate confidence score
        total_extractions = sum(len(v) for v in result.values())
        result['confidence'] = min(1.0, total_extractions / 10)  # 0.0 to 1.0

        return result

    def extract_categories_llm(self, issue: Dict, language: str = 'ko') -> Dict[str, List[str]]:
        """
        Extract categories using LLM with structured prompt

        Args:
            issue: Issue dictionary
            language: Target language for output

        Returns:
            Dictionary with symptom, cause, solution lists
        """
        if not self.llm_client:
            logger.warning("LLM client not available, skipping LLM extraction")
            return {'symptom': [], 'cause': [], 'solution': [], 'confidence': 0.0}

        # Prepare text content
        text_parts = []
        if issue.get('title'):
            text_parts.append(f"제목: {issue['title']}")
        if issue.get('description'):
            desc = issue['description'][:1000]  # Limit length
            text_parts.append(f"설명: {desc}")

        # Add key comments
        comments = issue.get('comments', [])
        if isinstance(comments, list) and comments:
            comment_texts = []
            for comment in comments[:3]:  # First 3 comments
                if isinstance(comment, dict):
                    content = comment.get('content', '')[:300]
                    if content:
                        comment_texts.append(content)

            if comment_texts:
                text_parts.append(f"주요 댓글:\n" + "\n---\n".join(comment_texts))

        issue_text = '\n\n'.join(text_parts)

        # Create structured prompt
        if language == 'ko':
            prompt = f"""다음 기술 이슈를 분석하여 현상, 원인, 대응방안을 추출하세요.

이슈 내용:
{issue_text}

아래 형식으로 정리하세요:

## 현상
- [발견된 증상이나 문제 현상을 나열]

## 원인
- [문제의 근본 원인을 나열]

## 대응방안
- [해결 방법이나 조치 사항을 나열]

각 항목은 bullet point로 간결하게 작성하세요."""
        elif language == 'ja':
            prompt = f"""次の技術問題を分析して、現象、原因、対応方法を抽出してください。

問題内容:
{issue_text}

以下の形式で整理してください:

## 現象
- [発見された症状や問題現象を列挙]

## 原因
- [問題の根本原因を列挙]

## 対応方法
- [解決方法や措置事項を列挙]

各項目は簡潔に箇条書きで記述してください。"""
        else:  # en
            prompt = f"""Analyze this technical issue and extract symptom, cause, and solution.

Issue content:
{issue_text}

Format your response as:

## Symptom
- [List observed symptoms or issues]

## Cause
- [List root causes]

## Solution
- [List fixes or workarounds]

Keep each bullet point concise."""

        try:
            response = self.llm_client.generate(prompt)

            # Parse LLM response
            result = self._parse_llm_response(response, language)
            result['confidence'] = 0.9  # High confidence for LLM

            return result

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {'symptom': [], 'cause': [], 'solution': [], 'confidence': 0.0}

    def _parse_llm_response(self, response: str, language: str) -> Dict[str, List[str]]:
        """Parse LLM response into structured categories"""

        result = {
            'symptom': [],
            'cause': [],
            'solution': []
        }

        # Define section headers by language
        if language == 'ko':
            headers = {
                'symptom': r'##\s*현상',
                'cause': r'##\s*원인',
                'solution': r'##\s*대응방안'
            }
        elif language == 'ja':
            headers = {
                'symptom': r'##\s*現象',
                'cause': r'##\s*原因',
                'solution': r'##\s*対応方法'
            }
        else:
            headers = {
                'symptom': r'##\s*Symptom',
                'cause': r'##\s*Cause',
                'solution': r'##\s*Solution'
            }

        # Extract each section
        for category, header_pattern in headers.items():
            # Find section
            match = re.search(f'{header_pattern}(.*?)(?=##|$)', response, re.DOTALL | re.IGNORECASE)

            if match:
                section_text = match.group(1).strip()

                # Extract bullet points
                bullets = re.findall(r'^[\s-]*[-•*]\s*(.+?)$', section_text, re.MULTILINE)

                # Clean and deduplicate
                cleaned = []
                for bullet in bullets:
                    bullet = bullet.strip()
                    if bullet and len(bullet) > 10 and bullet not in cleaned:
                        cleaned.append(bullet)

                result[category] = cleaned[:5]  # Limit to 5 per category

        return result

    def extract_categories(self, issue: Dict, use_llm: bool = False, language: str = 'ko') -> Dict[str, List[str]]:
        """
        Extract categories using hybrid approach

        Args:
            issue: Issue dictionary
            use_llm: Whether to use LLM refinement
            language: Target language

        Returns:
            Dictionary with symptom, cause, solution lists
        """
        # Step 1: Keyword-based extraction (fast, always runs)
        keyword_result = self.extract_categories_keyword(issue)

        logger.info(f"Keyword extraction confidence: {keyword_result.get('confidence', 0):.2f}")

        # Step 2: LLM refinement (optional, for low confidence or user request)
        if use_llm and (keyword_result.get('confidence', 0) < 0.5 or self.llm_client):
            logger.info("Running LLM refinement...")
            llm_result = self.extract_categories_llm(issue, language)

            # Merge results (LLM takes priority, keyword as fallback)
            merged = {
                'symptom': llm_result.get('symptom', []) or keyword_result.get('symptom', []),
                'cause': llm_result.get('cause', []) or keyword_result.get('cause', []),
                'solution': llm_result.get('solution', []) or keyword_result.get('solution', []),
                'confidence': max(keyword_result.get('confidence', 0), llm_result.get('confidence', 0)),
                'method': 'hybrid'
            }

            return merged

        # Return keyword-only result
        keyword_result['method'] = 'keyword'
        return keyword_result
