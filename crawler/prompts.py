"""
Few-Shot Prompt Templates for LLM Query Parsing

Provides language-specific examples for teaching LLM to convert
natural language queries to IMS search syntax.
"""

# English Few-Shot Examples
ENGLISH_PROMPT = """You are a query parser that converts natural language to IMS search syntax.

IMS Syntax Rules:
- AND (required terms): Use + before each term (example: +error +crash)
- OR (optional terms): Separate with spaces (example: error crash)
- Exact phrase: Wrap in single quotes (example: 'out of memory')
- Mixed: Combine operators (example: +error crash 'connection timeout')

Examples:

Query: find error and crash
IMS Syntax: +error +crash

Query: show connection or timeout
IMS Syntax: connection timeout

Query: find exact phrase "out of memory"
IMS Syntax: 'out of memory'

Query: find database error and crash or timeout
IMS Syntax: +database +error +crash timeout

Query: search for connection timeout issues
IMS Syntax: connection timeout issues

Query: get both authentication and authorization errors
IMS Syntax: +authentication +authorization +errors

Now convert this query:

Query: {query}
IMS Syntax:"""

# Korean Few-Shot Examples
KOREAN_PROMPT = """당신은 자연어를 IMS 검색 구문으로 변환하는 쿼리 파서입니다.

IMS 구문 규칙:
- AND (필수 단어): 각 단어 앞에 + 사용 (예: +에러 +크래시)
- OR (선택 단어): 공백으로 구분 (예: 에러 크래시)
- 정확한 구문: 작은따옴표로 감싸기 (예: '메모리 부족')
- 혼합: 연산자 조합 (예: +에러 크래시 '연결 타임아웃')

예제:

Query: 에러와 크래시 찾아줘
IMS Syntax: +에러 +크래시

Query: 연결 또는 타임아웃 보여줘
IMS Syntax: 연결 타임아웃

Query: 정확히 메모리 부족
IMS Syntax: '메모리 부족'

Query: 데이터베이스 에러 그리고 크래시 또는 타임아웃
IMS Syntax: +데이터베이스 +에러 +크래시 타임아웃

Query: 인증 문제 검색
IMS Syntax: 인증 문제

Query: 연결과 권한 에러 모두 찾기
IMS Syntax: +연결 +권한 +에러

이제 이 쿼리를 변환하세요:

Query: {query}
IMS Syntax:"""

# Japanese Few-Shot Examples
JAPANESE_PROMPT = """あなたは自然言語をIMS検索構文に変換するクエリパーサーです。

IMS構文ルール:
- AND (必須用語): 各用語の前に + を使用 (例: +エラー +クラッシュ)
- OR (オプション用語): スペースで区切る (例: エラー クラッシュ)
- 完全一致フレーズ: シングルクォートで囲む (例: 'メモリ不足')
- 混合: 演算子を組み合わせる (例: +エラー クラッシュ '接続タイムアウト')

例:

Query: エラーとクラッシュを検索
IMS Syntax: +エラー +クラッシュ

Query: 接続またはタイムアウト
IMS Syntax: 接続 タイムアウト

Query: 正確にメモリ不足
IMS Syntax: 'メモリ不足'

Query: データベース エラー および クラッシュ または タイムアウト
IMS Syntax: +データベース +エラー +クラッシュ タイムアウト

Query: 認証問題を検索
IMS Syntax: 認証 問題

Query: 接続と権限エラーの両方
IMS Syntax: +接続 +権限 +エラー

では、このクエリを変換してください:

Query: {query}
IMS Syntax:"""


def get_prompt_template(language: str) -> str:
    """
    Get few-shot prompt template for language

    Args:
        language: Language code ('en', 'ko', 'ja')

    Returns:
        Prompt template with {query} placeholder
    """
    prompts = {
        'en': ENGLISH_PROMPT,
        'ko': KOREAN_PROMPT,
        'ja': JAPANESE_PROMPT,
    }

    return prompts.get(language, ENGLISH_PROMPT)


def build_prompt(query: str, language: str) -> str:
    """
    Build complete prompt for LLM

    Args:
        query: Natural language query
        language: Language code

    Returns:
        Complete prompt ready for LLM
    """
    template = get_prompt_template(language)
    return template.format(query=query)
