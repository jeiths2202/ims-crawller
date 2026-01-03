# UserID별 Data Repository 구조 설계

## 📋 설계 개요

**목적**: 멀티 유저 환경에서 각 사용자의 크롤링 데이터와 리포트를 독립적으로 관리

**핵심 원칙**:
1. **사용자 격리**: 각 userid별로 완전히 독립된 데이터 공간
2. **세션 추적**: 각 크롤링 세션을 개별적으로 관리 및 추적
3. **리포트 중앙화**: 사용자별 모든 리포트를 한 곳에서 조회
4. **확장성**: 새로운 데이터 타입과 기능 추가 용이

## 🏗️ 디렉토리 구조

```
data/
└── users/                                    # 모든 사용자 데이터 루트
    └── {userid}/                             # 사용자별 독립 공간 (예: yijae.shin/)
        ├── sessions/                         # 크롤링 세션 데이터
        │   ├── {session_id}/                 # 개별 세션 (예: OpenFrame_TPETIME_20260103_120855/)
        │   │   ├── issues/                   # 이슈 JSON 파일들
        │   │   │   ├── 347863.json          # 이슈 상세 정보
        │   │   │   ├── 339659.json
        │   │   │   └── ...
        │   │   ├── attachments/              # 세션별 첨부파일
        │   │   │   ├── 347863/              # 이슈별 첨부파일
        │   │   │   │   ├── document.pdf
        │   │   │   │   ├── screenshot.png
        │   │   │   │   └── logs.txt
        │   │   │   └── 339659/
        │   │   ├── metadata.json            # 세션 메타정보
        │   │   └── session_report.md        # 세션별 자동 생성 리포트
        │   ├── {session_id_2}/
        │   └── ...
        │
        ├── reports/                          # 최종 분석 리포트 (중앙 관리)
        │   ├── daily/                       # 일별 리포트
        │   │   ├── summary_20260103.md
        │   │   └── summary_20260102.md
        │   ├── weekly/                      # 주별 리포트
        │   │   └── week_2026_01.md
        │   ├── monthly/                     # 월별 리포트
        │   │   └── analytics_2026_01.md
        │   └── custom/                      # 사용자 정의 리포트
        │       └── tpetime_analysis.md
        │
        ├── analytics/                        # 분석 데이터 및 통계
        │   ├── issue_stats.json             # 이슈 통계 (카테고리별, 제품별)
        │   ├── search_history.json          # 검색 이력
        │   ├── keyword_trends.json          # 키워드 트렌드 분석
        │   └── performance_metrics.json     # 크롤러 성능 지표
        │
        ├── cache/                            # 캐시 및 임시 데이터
        │   ├── query_cache.json             # 검색 쿼리 결과 캐시
        │   ├── session_cache.json           # 세션 상태 캐시
        │   └── embeddings/                  # 시맨틱 검색용 임베딩 캐시
        │       └── issue_embeddings.pkl
        │
        ├── exports/                          # 외부 시스템 연동용 내보내기
        │   ├── json/                        # JSON 형식 내보내기
        │   │   └── all_issues_20260103.json
        │   ├── csv/                         # CSV 형식 내보내기
        │   │   └── issue_summary.csv
        │   └── rag/                         # RAG 시스템용 데이터
        │       ├── documents/
        │       └── index/
        │
        ├── config/                           # 사용자별 설정
        │   ├── preferences.json             # 크롤링 설정, UI 설정
        │   ├── search_filters.json          # 저장된 검색 필터
        │   └── notification_rules.json      # 알림 규칙
        │
        └── logs/                             # 사용자별 로그
            ├── crawler_20260103.log         # 일별 크롤러 로그
            ├── errors.log                   # 에러 로그
            └── audit.log                    # 감사 로그 (작업 이력)
```

## 📄 파일 포맷 상세

### 1. Session Metadata (`metadata.json`)

세션 실행 정보와 결과 요약

```json
{
  "session_id": "OpenFrame_TPETIME_error_에러_오류_20260103_120855",
  "user_id": "yijae.shin",
  "created_at": "2026-01-03T12:08:55+09:00",
  "completed_at": "2026-01-03T12:12:30+09:00",
  "duration_seconds": 215,

  "search_config": {
    "product": "OpenFrame",
    "original_query": "TPETIME error의 발생원인과 대응방안에 대해서 알려줘",
    "parsed_query": "+TPETIME error 에러 오류",
    "language": "ko",
    "max_results": 20,
    "crawl_related": false
  },

  "results": {
    "total_issues": 10,
    "issues_crawled": 10,
    "attachments_downloaded": 45,
    "failed_issues": 0,
    "related_issues": 0
  },

  "issue_ids": [
    "347863", "344218", "339659", "337468", "336450",
    "326554", "326216", "326002", "325259", "322573"
  ],

  "performance": {
    "search_time_ms": 17000,
    "crawl_time_ms": 180000,
    "avg_issue_time_ms": 18000,
    "parallel_workers": 3
  },

  "errors": [],
  "warnings": [
    "Issue 347863: 2 attachments without download URLs"
  ]
}
```

### 2. Session Report (`session_report.md`)

세션별 자동 생성 리포트 (RAG 컨텍스트 포함)

```markdown
# 크롤링 세션 리포트

**세션 ID**: OpenFrame_TPETIME_error_에러_오류_20260103_120855
**사용자**: yijae.shin
**실행일시**: 2026-01-03 12:08:55 ~ 12:12:30 (3분 35초)

## 검색 조건

- **제품**: OpenFrame
- **원본 쿼리**: "TPETIME error의 발생원인과 대응방안에 대해서 알려줘"
- **파싱된 쿼리**: `+TPETIME error 에러 오류`
- **언어**: Korean (자동 감지)
- **최대 결과**: 20개

## 검색 결과

- **총 이슈 발견**: 10개
- **크롤링 완료**: 10개
- **첨부파일**: 45개 다운로드

### 발견된 이슈

| Issue ID | Title | Status | Priority |
|----------|-------|--------|----------|
| 347863 | [일본 동경해상] TPETIME 에러 분석 | Closed | High |
| 344218 | TPETIME timeout 발생 원인 | Open | Medium |
| ... | ... | ... | ... |

## 주요 인사이트

### 키워드 분석
- **TPETIME**: 10건 (100%)
- **에러/오류**: 6건 (60%)
- **error** (영어): 4건 (40%)

### 시맨틱 클러스터
1. **타임아웃 원인 분석** (5건)
2. **해결 방법 가이드** (3건)
3. **프로젝트 이슈** (2건)

## 다음 단계 제안

1. Issue 347863, 344218 심층 분석 (타임아웃 원인 공통점)
2. 해결 방법 문서화 (재발 방지)
3. 관련 이슈 추가 크롤링 (`--related` 옵션)
```

### 3. User Analytics (`analytics/issue_stats.json`)

사용자별 누적 통계

```json
{
  "user_id": "yijae.shin",
  "last_updated": "2026-01-03T12:12:30+09:00",
  "period": {
    "start": "2026-01-01T00:00:00+09:00",
    "end": "2026-01-03T23:59:59+09:00"
  },

  "totals": {
    "sessions": 15,
    "issues_crawled": 247,
    "attachments_downloaded": 1534,
    "unique_issues": 189
  },

  "by_product": {
    "OpenFrame": {"count": 150, "percentage": 60.7},
    "Tibero": {"count": 62, "percentage": 25.1},
    "JEUS": {"count": 35, "percentage": 14.2}
  },

  "by_status": {
    "Open": {"count": 78, "percentage": 31.6},
    "Closed": {"count": 142, "percentage": 57.5},
    "In Progress": {"count": 27, "percentage": 10.9}
  },

  "top_keywords": [
    {"keyword": "TPETIME", "count": 45, "trend": "increasing"},
    {"keyword": "error", "count": 38, "trend": "stable"},
    {"keyword": "timeout", "count": 32, "trend": "decreasing"}
  ],

  "search_patterns": {
    "avg_results_per_search": 16.5,
    "most_common_products": ["OpenFrame", "Tibero"],
    "peak_search_hours": [10, 14, 16],
    "languages_used": {"ko": 12, "en": 3}
  }
}
```

### 4. User Preferences (`config/preferences.json`)

사용자별 설정 및 선호도

```json
{
  "user_id": "yijae.shin",
  "crawler": {
    "default_product": "OpenFrame",
    "default_max_results": 50,
    "headless_mode": true,
    "parallel_workers": 3,
    "download_attachments": true,
    "crawl_related_issues": false
  },

  "natural_language": {
    "default_language": "ko",
    "auto_detect_language": true,
    "synonym_expansion": true,
    "intent_filtering": true
  },

  "reports": {
    "auto_generate_session_report": true,
    "include_semantic_analysis": true,
    "report_format": "markdown",
    "daily_summary": true,
    "email_reports": false
  },

  "notifications": {
    "on_session_complete": true,
    "on_new_high_priority_issue": true,
    "on_error": true
  },

  "ui": {
    "theme": "dark",
    "language": "ko",
    "items_per_page": 20
  }
}
```

## 🔄 데이터 흐름

```
사용자 검색 요청
    ↓
[Natural Language Parser]
    ↓
[IMS Search & Crawl]
    ↓
[Session 생성]
    ↓
data/users/{userid}/sessions/{session_id}/
    ├── issues/*.json          ← 이슈 데이터 저장
    ├── attachments/           ← 첨부파일 다운로드
    ├── metadata.json          ← 세션 정보 기록
    └── session_report.md      ← 자동 리포트 생성
    ↓
[Analytics 업데이트]
    ↓
data/users/{userid}/analytics/
    ├── issue_stats.json       ← 통계 갱신
    ├── search_history.json    ← 검색 이력 추가
    └── keyword_trends.json    ← 트렌드 분석
    ↓
[Daily Report 생성] (자동 스케줄)
    ↓
data/users/{userid}/reports/daily/
    └── summary_20260103.md    ← 일일 요약 리포트
```

## 📊 리포트 계층 구조

### 1단계: Session Report (실시간)
- **생성 시점**: 크롤링 완료 즉시
- **위치**: `sessions/{session_id}/session_report.md`
- **내용**: 개별 세션 결과, 발견한 이슈 목록, 기본 분석

### 2단계: Daily Report (일별)
- **생성 시점**: 매일 자정 (또는 첫 세션 완료 시)
- **위치**: `reports/daily/summary_YYYYMMDD.md`
- **내용**: 당일 모든 세션 통합, 일일 통계, 주요 발견사항

### 3단계: Weekly Report (주별)
- **생성 시점**: 매주 일요일
- **위치**: `reports/weekly/week_YYYY_WW.md`
- **내용**: 주간 트렌드, 이슈 패턴 분석, 해결 현황

### 4단계: Monthly Report (월별)
- **생성 시점**: 매월 말일
- **위치**: `reports/monthly/analytics_YYYY_MM.md`
- **내용**: 월간 심층 분석, 제품별 품질 지표, 개선 제안

### 5단계: Custom Report (사용자 정의)
- **생성 시점**: 사용자 요청 시
- **위치**: `reports/custom/{report_name}.md`
- **내용**: 특정 키워드/제품/기간 맞춤 분석

## 🔐 권한 및 접근 제어

```
data/users/
├── yijae.shin/          # Owner: yijae.shin (rwx)
│   └── ...              # 본인만 접근 가능
├── john.doe/            # Owner: john.doe (rwx)
│   └── ...              # 본인만 접근 가능
└── admin/               # Owner: admin (rwx)
    └── system_reports/  # 전체 사용자 통합 리포트
```

**접근 규칙**:
- 각 사용자는 자신의 디렉토리만 읽기/쓰기 가능
- 관리자는 모든 사용자 데이터 읽기 전용 접근
- 시스템 리포트는 관리자만 생성 가능

## 🛠️ 구현 단계

### Phase 1: 기본 구조 생성 (1주)
- [ ] UserRepository 클래스 구현
- [ ] 디렉토리 자동 생성 로직
- [ ] Session metadata 관리
- [ ] 기존 데이터 마이그레이션

### Phase 2: 리포트 자동화 (1주)
- [ ] Session report 자동 생성
- [ ] Daily report 스케줄러
- [ ] Analytics 데이터 수집
- [ ] 리포트 템플릿 시스템

### Phase 3: 고급 기능 (2주)
- [ ] Weekly/Monthly report 생성
- [ ] Custom report 빌더
- [ ] Export 기능 (JSON, CSV, RAG)
- [ ] 트렌드 분석 및 시각화

### Phase 4: 멀티 유저 지원 (1주)
- [ ] 사용자 인증 통합
- [ ] 권한 관리 시스템
- [ ] 공유 기능
- [ ] 관리자 대시보드

## 💡 주요 이점

### 1. 사용자 독립성
- 각 사용자가 독립적인 작업 공간 보유
- 데이터 충돌 없음
- 개인별 설정 및 선호도 관리

### 2. 세션 추적성
- 모든 크롤링 세션 이력 보존
- 검색 패턴 분석 가능
- 재현 가능한 검색 (metadata 기반)

### 3. 리포트 중앙화
- 모든 리포트를 한 곳에서 조회
- 시계열 분석 용이
- RAG 시스템 통합 간편

### 4. 확장성
- 새로운 데이터 타입 추가 용이
- 플러그인 아키텍처 지원
- 외부 시스템 연동 간편

### 5. 유지보수성
- 명확한 디렉토리 구조
- 일관된 파일 포맷
- 자동화된 데이터 관리

## 🔄 마이그레이션 전략

### 기존 구조 → 새 구조

```bash
# Before
data/
├── crawl_sessions/
│   └── OpenFrame_TPETIME_20260103_120855/
│       └── *.json
└── attachments/
    └── {issue_id}/

# After
data/users/yijae.shin/
├── sessions/
│   └── OpenFrame_TPETIME_20260103_120855/
│       ├── issues/*.json
│       └── attachments/
└── reports/
```

**마이그레이션 스크립트** (`migrate_to_userid_structure.py`):
1. 기존 세션 폴더 인식
2. userid 추출 (metadata 또는 .env)
3. 새 구조로 파일 이동
4. metadata.json 생성
5. 백업 생성

## 📝 구현 예시

### UserRepository 클래스

```python
class UserRepository:
    """사용자별 데이터 저장소 관리"""

    def __init__(self, user_id: str, base_path: Path = Path("data/users")):
        self.user_id = user_id
        self.root = base_path / user_id
        self._ensure_structure()

    def _ensure_structure(self):
        """필요한 디렉토리 구조 생성"""
        dirs = [
            self.root / "sessions",
            self.root / "reports" / "daily",
            self.root / "reports" / "weekly",
            self.root / "reports" / "monthly",
            self.root / "reports" / "custom",
            self.root / "analytics",
            self.root / "cache",
            self.root / "exports" / "json",
            self.root / "exports" / "csv",
            self.root / "exports" / "rag",
            self.root / "config",
            self.root / "logs"
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def create_session(self, session_id: str) -> "Session":
        """새 크롤링 세션 생성"""
        session_path = self.root / "sessions" / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        (session_path / "issues").mkdir(exist_ok=True)
        (session_path / "attachments").mkdir(exist_ok=True)

        return Session(
            session_id=session_id,
            user_id=self.user_id,
            path=session_path
        )

    def get_sessions(self, limit: int = None) -> List["Session"]:
        """세션 목록 조회 (최신순)"""
        sessions_dir = self.root / "sessions"
        session_dirs = sorted(
            sessions_dir.iterdir(),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if limit:
            session_dirs = session_dirs[:limit]

        return [
            Session.from_path(d, self.user_id)
            for d in session_dirs
        ]

    def generate_daily_report(self, date: datetime.date) -> Path:
        """일일 리포트 생성"""
        # 해당 날짜의 모든 세션 수집
        # 통계 계산
        # 리포트 마크다운 생성
        # reports/daily/summary_YYYYMMDD.md 저장
        pass
```

---

**작성일**: 2026-01-03
**작성자**: Claude Code
**상태**: ✅ 설계 완료 (구현 대기)
