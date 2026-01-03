# Natural Language Parser 심층 분석 및 개선 방안

## 문제 정의

### 현재 상황
**입력 쿼리**: "TPETIME error의 발생원인과 대응방안에 대해서 알려줘"

**현재 파싱 결과**: `+TPETIME +error +발생원인 +대응방안`
- 4개의 필수(AND) 키워드로 처리
- 너무 제한적 → 검색 결과 0건

**문제점**:
- "발생원인" (cause/reason) = 검색 **의도**, 실제 키워드 아님
- "대응방안" (countermeasure/solution) = 검색 **의도**, 실제 키워드 아님
- 이 단어들은 "원인을 알려줘", "해결책을 알려줘"라는 의미

### 이상적인 파싱 결과
**Option 1 (보수적)**: `+TPETIME +error`
- TPETIME 필수, error 필수
- 원인/방안은 의도이므로 제거

**Option 2 (균형)**: `+TPETIME error`
- TPETIME만 필수 (기술 용어)
- error는 선택적 (일반 키워드)

**Option 3 (공격적)**: `TPETIME error`
- 모두 OR 검색
- 가장 넓은 검색

---

## 1. 한국어 질문 패턴 분석

### 의도 표현 패턴 (Intent Patterns)

#### 원인 문의 패턴
```
~의 원인       "TPETIME의 원인"
~발생 원인     "TPETIME 발생 원인"
~발생원인      "TPETIME 발생원인"
왜 ~          "왜 TPETIME이 발생하는지"
어떤 이유로 ~   "어떤 이유로 TPETIME이 발생하는지"
```

#### 해결책 문의 패턴
```
~의 해결책     "TPETIME의 해결책"
~의 대응방안    "TPETIME의 대응방안"
~의 처리방법    "TPETIME의 처리방법"
~를 해결      "TPETIME를 해결하는 방법"
어떻게 ~      "어떻게 TPETIME을 해결하는지"
```

#### 정보 요청 패턴
```
~에 대해서     "TPETIME에 대해서"
~에 대한      "TPETIME에 대한 정보"
~에 관한      "TPETIME에 관한 내용"
~를 알려줘    "TPETIME를 알려줘"
~를 보여줘    "TPETIME를 보여줘"
```

### 의도 단어 분류

#### 원인 관련 의도 단어
```
원인, 발생원인, 이유, 사유, 배경, 계기
발생, 발생이유, 발생배경, 근본원인
```

#### 해결책 관련 의도 단어
```
해결, 해결책, 해결방안, 해결방법
대응, 대응방안, 대응책
처리, 처리방법, 조치, 조치사항
```

#### 정보 요청 의도 단어
```
정보, 내용, 설명, 상세, 자세히
가이드, 문서, 매뉴얼
```

---

## 2. 합성어 분해 분석

### 한국어 합성어 특성
한국어는 명사 합성이 자유로움:
- 발생 + 원인 = 발생원인
- 대응 + 방안 = 대응방안
- 처리 + 방법 = 처리방법

### 합성어 분해 전략

#### Case 1: 둘 다 low_priority_words인 경우
```python
"발생원인" = "발생" + "원인"
  ↓
둘 다 low_priority_words → 전체 단어 제거

"대응방안" = "대응" + "방안"
  ↓
둘 다 low_priority_words → 전체 단어 제거
```

#### Case 2: 하나만 low_priority_words인 경우
```python
"에러원인" = "에러" + "원인"
  ↓
"원인"은 low_priority → "에러"만 추출

"TPETIME발생" = "TPETIME" + "발생"
  ↓
"발생"은 low_priority → "TPETIME"만 추출
```

#### Case 3: 둘 다 의미있는 경우
```python
"배치작업" = "배치" + "작업"
  ↓
둘 다 의미있음 → 전체 단어 유지
```

---

## 3. 개선 방안

### 방안 1: Intent Pattern Recognition (추천 ⭐)

**개념**: 질문 의도 패턴을 감지하고 제거

**구현**:
```python
# nl_patterns.py에 추가
'ko': {
    # 의도 패턴 (검색어가 아닌 의도 표현)
    'intent_patterns': [
        # 원인 문의
        r'(.+?)(의\s*)?원인',           # "~의 원인", "~원인"
        r'(.+?)(의\s*)?이유',           # "~의 이유"
        r'(.+?)(의\s*)?사유',
        r'(.+?)(발생\s*)?배경',

        # 해결책 문의
        r'(.+?)(의\s*)?해결(책|방안|방법)?',  # "~의 해결책"
        r'(.+?)(의\s*)?대응(책|방안)?',      # "~의 대응방안"
        r'(.+?)(의\s*)?처리방(법|안)',
        r'(.+?)(를\s*)?(해결|처리|조치)',

        # 정보 요청
        r'(.+?)(에\s*)?대해(서)?',       # "~에 대해서"
        r'(.+?)(에\s*)?관(해|한)',       # "~에 관한"
        r'(.+?)(를\s*)?(알려|보여|설명)',
    ],

    # 의도 키워드 (단독으로 나타나는 의도 표현)
    'intent_keywords': [
        # 원인 관련
        '원인', '발생원인', '이유', '사유', '배경', '계기',

        # 해결책 관련
        '해결', '해결책', '해결방안', '해결방법',
        '대응', '대응방안', '대응책',
        '처리', '처리방법', '조치', '조치사항',

        # 정보 요청
        '정보', '내용', '설명', '상세', '가이드',
    ]
}
```

**적용 예시**:
```
입력: "TPETIME error의 발생원인과 대응방안에 대해서 알려줘"

1단계: 패턴 매칭
- "발생원인" → intent pattern 매칭 → 제거
- "대응방안" → intent pattern 매칭 → 제거
- "대해서" → intent pattern 매칭 → 제거
- "알려줘" → verb로 제거

2단계: 남은 키워드
- "TPETIME error"

3단계: 우선순위 분류
- TPETIME → high priority (대문자 기술 용어)
- error → medium priority (일반 단어)

최종 결과: "+TPETIME error"
```

### 방안 2: Compound Word Decomposition

**개념**: 합성어를 분해하여 각 부분이 low_priority인지 확인

**구현**:
```python
def _decompose_korean_compound(self, word: str, language: str) -> str:
    """
    한국어 합성어 분해 및 필터링

    Returns:
        - 의미있는 부분만 반환
        - 모두 low_priority면 None
    """
    if language != 'ko':
        return word

    patterns = self.patterns.get_patterns('ko')
    low_priority = patterns.get('low_priority_words', [])
    intent_keywords = patterns.get('intent_keywords', [])

    # 전체 단어가 intent keyword면 제거
    if word in intent_keywords:
        return None

    # 합성어 후보 (2-5글자)
    if len(word) < 2 or len(word) > 10:
        return word

    # 가능한 분해 시도
    for i in range(1, len(word)):
        left = word[:i]
        right = word[i:]

        # 둘 다 의도/low_priority 단어인 경우
        if (left in low_priority or left in intent_keywords) and \
           (right in low_priority or right in intent_keywords):
            return None  # 전체 제거

        # 왼쪽만 의미있는 경우
        if left not in low_priority and left not in intent_keywords and \
           (right in low_priority or right in intent_keywords):
            return left

        # 오른쪽만 의미있는 경우
        if (left in low_priority or left in intent_keywords) and \
           right not in low_priority and right not in intent_keywords:
            return right

    # 분해 실패 시 원본 반환
    return word
```

**적용 예시**:
```
"발생원인" → "발생" + "원인" → 둘 다 low_priority → None (제거)
"대응방안" → "대응" + "방안" → 둘 다 low_priority → None (제거)
"에러원인" → "에러" + "원인" → "에러"만 추출
```

### 방안 3: Contextual Priority Scoring

**개념**: 단어의 우선순위를 컨텍스트 기반으로 동적 계산

**구현**:
```python
def _calculate_term_score(self, term: str, context: List[str], language: str) -> float:
    """
    컨텍스트 기반 키워드 점수 계산

    점수 기준:
    - 1.0: 필수 키워드 (AND)
    - 0.5: 선택 키워드 (OR)
    - 0.0: 제거 대상
    """
    patterns = self.patterns.get_patterns(language)

    score = 0.5  # 기본값: medium priority

    # 1. High priority patterns 체크
    for pattern in patterns.get('high_priority_patterns', []):
        if re.match(pattern, term):
            score = 1.0
            break

    # 2. Intent keywords 체크 (감점)
    if term in patterns.get('intent_keywords', []):
        score = 0.0

    # 3. Low priority words 체크 (감점)
    if term in patterns.get('low_priority_words', []):
        score = 0.0

    # 4. 합성어 분해 후 재평가
    decomposed = self._decompose_korean_compound(term, language)
    if decomposed != term:
        if decomposed is None:
            score = 0.0
        else:
            # 재귀적으로 분해된 부분 평가
            return self._calculate_term_score(decomposed, context, language)

    # 5. 컨텍스트 기반 조정
    # 기술 용어와 함께 나타나면 중요도 상승
    tech_terms_in_context = [t for t in context
                            if re.match(r'[A-Z][A-Z0-9]{3,}', t)]
    if tech_terms_in_context and score > 0:
        score = min(1.0, score + 0.2)

    return score
```

**적용 예시**:
```
쿼리: "TPETIME error의 발생원인과 대응방안"
컨텍스트: ["TPETIME", "error", "발생원인", "대응방안"]

TPETIME → 1.0 (high_priority_pattern)
error → 0.7 (medium + tech context boost)
발생원인 → 0.0 (intent_keyword)
대응방안 → 0.0 (intent_keyword)

최종: "+TPETIME error" (1.0 이상은 +, 0.5 이상은 공백, 0.0은 제거)
```

---

## 4. 구현 우선순위

### Phase 1: Intent Pattern Recognition (즉시 적용 가능)
**구현 시간**: 1-2시간
**효과**: 높음 ⭐⭐⭐
**복잡도**: 낮음

1. `nl_patterns.py`에 `intent_keywords` 추가
2. `_extract_terms()`에서 intent_keywords 필터링
3. 기존 로직 재사용 가능

### Phase 2: Compound Word Decomposition (중기)
**구현 시간**: 3-4시간
**효과**: 중간 ⭐⭐
**복잡도**: 중간

1. 합성어 분해 로직 추가
2. 재귀적 평가 구현
3. 엣지 케이스 처리

### Phase 3: Contextual Scoring (장기)
**구현 시간**: 5-6시간
**효과**: 높음 ⭐⭐⭐
**복잡도**: 높음

1. 점수 계산 시스템 구현
2. 동적 임계값 설정
3. 학습 데이터 기반 튜닝

---

## 5. 테스트 케이스

### 원인 문의 쿼리
```python
test_cases = [
    {
        'input': 'TPETIME error의 발생원인과 대응방안에 대해서 알려줘',
        'expected': '+TPETIME error',
        'explanation': '의도 단어(발생원인, 대응방안) 제거'
    },
    {
        'input': 'TPETIME이 왜 발생하는지 원인을 알려줘',
        'expected': '+TPETIME',
        'explanation': '의도 표현(왜, 원인) 제거'
    },
    {
        'input': 'timeout error 해결방법',
        'expected': 'timeout error',
        'explanation': '해결방법은 의도 단어'
    },
]
```

### 기술 용어 쿼리
```python
test_cases = [
    {
        'input': 'OpenFrame TPETIME 처리 가이드',
        'expected': '+OpenFrame +TPETIME',
        'explanation': '처리, 가이드는 의도 단어'
    },
    {
        'input': 'RC16 에러 대응방안',
        'expected': '+RC16',
        'explanation': 'RC16만 핵심, 에러/대응방안은 보조'
    },
]
```

### 복합 쿼리
```python
test_cases = [
    {
        'input': 'batch job failure의 원인과 해결책을 알려줘',
        'expected': '+batch +job +failure',
        'explanation': '영어는 모두 의미있는 키워드'
    },
    {
        'input': 'OpenFrame에서 TPETIME error 발생 시 조치사항',
        'expected': '+OpenFrame +TPETIME error',
        'explanation': 'OpenFrame/TPETIME 필수, error 선택'
    },
]
```

---

## 6. 추천 구현 순서

### Step 1: Intent Keywords 추가 (30분)
```python
# nl_patterns.py
'intent_keywords': [
    '원인', '발생원인', '이유', '사유',
    '해결', '해결책', '해결방안', '대응', '대응방안',
    '처리', '조치', '가이드', '정보', '내용'
]
```

### Step 2: Intent Filtering 구현 (30분)
```python
# nl_parser.py _extract_terms()
# Check if term is intent keyword
if language == 'ko' and term in patterns.get('intent_keywords', []):
    continue  # Skip intent keywords
```

### Step 3: 테스트 및 검증 (30분)
```python
# test_nl_parser.py
def test_korean_intent_filtering():
    parser = NaturalLanguageParser()
    result = parser.parse("TPETIME error의 발생원인과 대응방안에 대해서 알려줘")
    assert result.ims_query == "+TPETIME error"
```

### Step 4: 실제 크롤링 검증 (15분)
```bash
python main.py crawl -p "OpenFrame" \
  -k "TPETIME error의 발생원인과 대응방안에 대해서 알려줘" \
  -m 10 --no-confirm
```

---

## 7. 예상 개선 효과

### 현재 (Before)
```
입력: "TPETIME error의 발생원인과 대응방안에 대해서 알려줘"
파싱: "+TPETIME +error +발생원인 +대응방안"
결과: 검색 결과 0건 (너무 제한적)
정확도: 0%
```

### 개선 후 (After - Phase 1)
```
입력: "TPETIME error의 발생원인과 대응방안에 대해서 알려줘"
파싱: "+TPETIME error"
결과: TPETIME 포함 이슈들 반환
정확도: 예상 70-80%
```

### 최종 (After - Phase 3)
```
입력: "TPETIME error의 발생원인과 대응방안에 대해서 알려줘"
파싱: "+TPETIME error" (컨텍스트 기반 최적화)
결과: 관련성 높은 이슈 우선 반환
정확도: 예상 85-90%
```

---

## 결론

**가장 효과적인 개선 방안**: **Intent Pattern Recognition (방안 1)**
- 빠른 구현 (1-2시간)
- 즉각적인 효과
- 기존 코드 최소 변경

**추가 개선**: Compound Word Decomposition과 Contextual Scoring을 순차적으로 적용하여 정확도를 점진적으로 향상

**다음 단계**: Phase 1 구현 및 테스트
