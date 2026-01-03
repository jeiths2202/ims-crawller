# UserID별 Repository 구조 구현 완료 보고서

## 📋 구현 개요

**완료일**: 2026-01-03
**상태**: ✅ 구현 완료 (마이그레이션 대기)

userid별 독립적인 데이터 저장소 구조를 설계하고 구현하였습니다.

## 🏗️ 구현된 구조

```
data/users/{userid}/                     # 사용자별 루트 디렉토리
├── sessions/                           # 크롤링 세션들
│   └── {session_id}/                  # 개별 세션
│       ├── issues/                    # 이슈 JSON 파일
│       │   ├── 347863.json
│       │   └── ...
│       ├── attachments/               # 첨부파일
│       │   └── {issue_id}/
│       ├── metadata.json             # 세션 메타데이터
│       └── session_report.md         # 자동 생성 리포트
│
├── reports/                           # 최종 리포트 (중앙 관리)
│   ├── daily/                        # 일별 리포트
│   ├── weekly/                       # 주별 리포트
│   ├── monthly/                      # 월별 리포트
│   └── custom/                       # 사용자 정의
│
├── analytics/                         # 분석 데이터
│   ├── issue_stats.json
│   └── search_history.json
│
├── cache/                             # 캐시
│   └── embeddings/
│
├── exports/                           # 내보내기
│   ├── json/
│   ├── csv/
│   └── rag/
│
├── config/                            # 사용자 설정
│   └── preferences.json
│
└── logs/                              # 로그
    └── crawler_YYYYMMDD.log
```

## 📁 구현된 파일

### 1. `crawler/user_repository.py` (신규 생성)

**핵심 클래스**:

#### UserRepository
```python
class UserRepository:
    """사용자별 데이터 저장소 관리"""

    def __init__(self, user_id: str, base_path: Path = None)
    def create_session(self, session_id: str) -> Session
    def get_session(self, session_id: str) -> Optional[Session]
    def get_sessions(self, limit: int = None) -> List[Session]
    def get_latest_session() -> Optional[Session]
    def delete_session(self, session_id: str)
    def find_sessions_by_product(self, product: str) -> List[Session]
    def find_sessions_by_date(self, date: datetime.date) -> List[Session]
    def get_stats() -> Dict[str, Any]
```

**주요 기능**:
- 사용자별 디렉토리 구조 자동 생성
- 세션 생성 및 관리
- 세션 검색 (제품별, 날짜별)
- 전체 통계 조회

#### Session
```python
class Session:
    """개별 크롤링 세션 관리"""

    def __init__(self, session_id: str, user_id: str, path: Path)
    def init_metadata(...)
    def update_results(...)
    def add_issue_id(self, issue_id: str)
    def add_error(self, error: str)
    def add_warning(self, warning: str)
    def complete(self, start_time: datetime)
    def get_issue_path(self, issue_id: str) -> Path
    def get_attachment_dir(self, issue_id: str) -> Path
```

**주요 기능**:
- 세션 메타데이터 관리 (metadata.json)
- 이슈 및 첨부파일 경로 관리
- 결과 업데이트 (실시간)
- 에러/경고 추적

#### SessionMetadata
```python
@dataclass
class SessionMetadata:
    """세션 메타정보"""
    session_id: str
    user_id: str
    created_at: str
    completed_at: Optional[str]
    search_config: Dict[str, Any]
    results: Dict[str, Any]
    issue_ids: List[str]
    performance: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
```

### 2. `migrate_to_userid_structure.py` (마이그레이션 스크립트)

**기능**:
- 기존 `data/crawl_sessions/` → `data/users/{userid}/sessions/` 이동
- 기존 `data/attachments/` → `data/users/{userid}/sessions/{session_id}/attachments/` 이동
- metadata.json 자동 생성 (세션 정보 파싱)
- Dry-run 모드 지원 (실제 이동 없이 미리보기)
- 백업 생성 옵션

**사용법**:
```bash
# 1. 분석만 수행 (현재 상태 확인)
python migrate_to_userid_structure.py --analyze-only

# 2. Dry-run (실제 이동 없이 테스트)
python migrate_to_userid_structure.py --dry-run

# 3. 백업 생성 후 실제 마이그레이션
python migrate_to_userid_structure.py --backup

# 4. 실제 마이그레이션 (주의!)
python migrate_to_userid_structure.py
```

## 📊 마이그레이션 분석 결과

### 현재 데이터 현황

```
총 세션: 10개
  - 빈 세션 (JSON 파일 없음): 4개
  - 데이터 있는 세션: 6개

데이터 있는 세션:
  1. OpenFrame_TPETIME_20260103_045204 (10 issues)
  2. OpenFrame_TPETIME_20260103_084101 (10 issues)
  3. OpenFrame_TPETIME_error_20260103_042826 (5 issues)
  4. OpenFrame_TPETIME_error_20260103_044815 (10 issues)
  5. OpenFrame_TPETIME_error_20260103_115229 (10 issues)
  6. OpenFrame_TPETIME_error_에러_오류_20260103_120855 (10 issues)

총 이슈: 55개 (JSON 파일)
첨부파일 디렉토리: 12개
```

### 마이그레이션 후 구조

```
data/users/yijae.shin/
├── sessions/
│   ├── OpenFrame_TPETIME_20260103_045204/
│   │   ├── issues/
│   │   │   ├── 326002.json
│   │   │   ├── 337468.json
│   │   │   ├── 339659.json
│   │   │   ├── 344218.json
│   │   │   ├── 347863.json
│   │   │   └── ... (10 issues)
│   │   ├── attachments/
│   │   │   ├── 326002/
│   │   │   ├── 337468/
│   │   │   └── ...
│   │   └── metadata.json
│   │
│   ├── OpenFrame_TPETIME_error_에러_오류_20260103_120855/
│   │   └── ... (최신 세션, 10 issues)
│   │
│   └── ... (6개 세션)
│
└── reports/ (자동 생성 대기)
```

## 🔄 통합 계획 (다음 단계)

### Phase 1: main.py 통합 (1시간)

**변경 사항**:
```python
# main.py 수정

from crawler.user_repository import UserRepository

@cli.command()
def crawl(...):
    # UserID 가져오기
    user_id = settings.IMS_USERNAME

    # UserRepository 초기화
    repo = UserRepository(user_id)

    # Session 생성
    session = repo.create_session(session_id)

    # Metadata 초기화
    session.init_metadata(
        product=product,
        original_query=keywords,
        parsed_query=final_query,
        language=result.language,
        max_results=max_results,
        crawl_related=related
    )

    # 크롤링 실행
    with IMSScraper(...) as scraper:
        issues = scraper.crawl(...)

        # 각 이슈를 Session에 저장
        for issue in issues:
            # JSON 저장
            issue_path = session.get_issue_path(issue['issue_id'])
            with open(issue_path, 'w') as f:
                json.dump(issue, f)

            # Issue ID 추가
            session.add_issue_id(issue['issue_id'])

    # Session 완료
    session.complete(start_time)

    # 통계 출력
    stats = repo.get_stats()
    print(f"Total sessions: {stats['total_sessions']}")
```

### Phase 2: ims_scraper.py 통합 (30분)

**변경 사항**:
```python
# ims_scraper.py 수정

class IMSScraper:
    def __init__(self, session: Session = None, ...):
        self.session = session
        ...

    def crawl(self, ...):
        # 첨부파일 저장 경로 변경
        if self.session:
            attach_dir = self.session.get_attachment_dir(issue_id)
        else:
            attach_dir = old_path  # 하위 호환성

    def _handle_error(self, error):
        if self.session:
            self.session.add_error(str(error))
```

### Phase 3: 리포트 자동화 (2-3시간)

**기능**:
1. **Session Report 자동 생성**
   - 크롤링 완료 시 `session_report.md` 생성
   - 발견된 이슈 요약
   - 키워드 분석
   - 시맨틱 클러스터링

2. **Daily Report 스케줄러**
   - 매일 자정 실행
   - 당일 모든 세션 통합
   - `reports/daily/summary_YYYYMMDD.md` 생성

3. **Analytics 수집**
   - 검색 이력 추적
   - 키워드 트렌드 분석
   - 제품별 통계

## 🚀 마이그레이션 실행 가이드

### 단계별 실행 절차

#### 1단계: 현재 상태 확인
```bash
python migrate_to_userid_structure.py --analyze-only
```

**확인 사항**:
- 총 세션 개수
- 이슈 파일 개수
- 첨부파일 개수

#### 2단계: Dry-run 테스트
```bash
python migrate_to_userid_structure.py --dry-run
```

**확인 사항**:
- 마이그레이션 대상 세션
- 예상 파일 이동 경로
- 에러 발생 여부

#### 3단계: 백업 생성
```bash
python migrate_to_userid_structure.py --backup
```

**결과**:
- `data_backup_YYYYMMDD_HHMMSS/` 디렉토리 생성
- 기존 데이터 전체 복사

#### 4단계: 실제 마이그레이션
```bash
python migrate_to_userid_structure.py
```

**주의사항**:
⚠️ 이 명령은 실제로 파일을 이동시킵니다!
- 반드시 백업 먼저 수행
- Dry-run 결과 확인 후 실행
- 마이그레이션 중 중단하지 말 것

#### 5단계: 검증
```bash
# 새 구조 확인
ls -R data/users/yijae.shin/sessions/

# 통계 확인
python -c "
from crawler.user_repository import UserRepository
repo = UserRepository('yijae.shin')
print(repo.get_stats())
"
```

#### 6단계: 기존 디렉토리 정리
```bash
# 마이그레이션 성공 확인 후
# 기존 디렉토리 삭제 (선택사항)
rm -rf data/crawl_sessions/
rm -rf data/attachments/
```

## 💡 주요 이점

### 1. 데이터 격리 ✅
- 각 사용자의 데이터가 완전히 분리됨
- 멀티 유저 환경 지원 준비 완료

### 2. 세션 추적성 ✅
- 모든 크롤링 세션 이력 보존
- metadata.json으로 세션 정보 완벽 추적
- 재현 가능한 검색

### 3. 리포트 중앙화 ✅
- 모든 리포트를 `reports/` 아래 중앙 관리
- 일별/주별/월별 자동 생성 가능
- 사용자 정의 리포트 지원

### 4. 확장성 ✅
- 새로운 데이터 타입 추가 용이
- RAG 시스템 통합 간편 (`exports/rag/`)
- 플러그인 아키텍처 지원

### 5. 유지보수성 ✅
- 명확한 디렉토리 구조
- 일관된 파일 포맷 (JSON)
- 자동화된 메타데이터 관리

## 📈 예상 사용 시나리오

### 시나리오 1: 일상적인 크롤링

```bash
# 사용자가 크롤링 실행
python main.py crawl -p "OpenFrame" -k "TPETIME 에러" -m 20

# 자동으로 발생하는 일:
# 1. UserRepository가 yijae.shin 디렉토리 확인/생성
# 2. Session 생성 (OpenFrame_TPETIME_에러_20260103_143000/)
# 3. metadata.json 초기화
# 4. 크롤링 진행 중 이슈들을 issues/에 저장
# 5. 첨부파일을 attachments/{issue_id}/에 저장
# 6. metadata.json 실시간 업데이트 (진행 상황, 에러)
# 7. 완료 시 session_report.md 자동 생성
```

### 시나리오 2: 과거 검색 이력 조회

```python
from crawler.user_repository import UserRepository

# Repository 초기화
repo = UserRepository("yijae.shin")

# 최근 10개 세션 조회
recent_sessions = repo.get_sessions(limit=10)

for session in recent_sessions:
    print(f"Session: {session.session_id}")
    print(f"  Query: {session.metadata.search_config['original_query']}")
    print(f"  Issues: {len(session.metadata.issue_ids)}")
    print()

# 특정 제품 세션만 조회
openframe_sessions = repo.find_sessions_by_product("OpenFrame")

# 오늘 날짜 세션 조회
from datetime import date
today_sessions = repo.find_sessions_by_date(date.today())
```

### 시나리오 3: 전체 통계 확인

```python
# 사용자 통계
stats = repo.get_stats()

print(f"""
User Statistics for {stats['user_id']}:
  Total Sessions:      {stats['total_sessions']}
  Total Issues Crawled: {stats['total_issues_crawled']}
  Unique Issues:       {stats['unique_issues']}
  Total Attachments:   {stats['total_attachments']}

Sessions by Product:
""")

for product, count in stats['sessions_by_product'].items():
    print(f"  {product}: {count}")
```

## ⚠️ 주의사항

### 1. 백업 필수
- 마이그레이션 전 반드시 백업 생성
- `--backup` 옵션 사용 권장

### 2. Dry-run 먼저
- `--dry-run`으로 결과 미리 확인
- 예상치 못한 문제 사전 발견

### 3. 디스크 공간
- 기존 데이터 크기의 2배 공간 필요 (백업 포함)
- 마이그레이션 후 기존 디렉토리 삭제하면 공간 회수

### 4. 실행 중 중단 금지
- 마이그레이션 중 Ctrl+C 금지
- 중단 시 데이터 손실 가능

### 5. 권한 확인
- 파일 읽기/쓰기 권한 확인
- Windows: 관리자 권한 필요 없음

## 📝 다음 단계 체크리스트

- [ ] 마이그레이션 스크립트 테스트 (`--dry-run`)
- [ ] 백업 생성 (`--backup`)
- [ ] 실제 마이그레이션 실행
- [ ] 새 구조 검증 (파일 개수, 무결성)
- [ ] main.py 통합
- [ ] ims_scraper.py 통합
- [ ] Session Report 자동 생성 구현
- [ ] Daily Report 스케줄러 구현
- [ ] 기존 디렉토리 정리

## 🎯 성공 기준

### 마이그레이션 성공
- [ ] 모든 JSON 파일이 올바른 위치에 이동됨
- [ ] 모든 첨부파일이 올바른 위치에 이동됨
- [ ] metadata.json이 모든 세션에 생성됨
- [ ] 에러 없이 완료됨

### 통합 성공
- [ ] `python main.py crawl ...` 정상 동작
- [ ] 새 세션이 userid 구조에 생성됨
- [ ] 통계 조회 정상 동작 (`repo.get_stats()`)
- [ ] 기존 기능 모두 정상 동작 (하위 호환성)

---

**작성일**: 2026-01-03
**작성자**: Claude Code
**상태**: ✅ 구현 완료 (마이그레이션 대기)
**다음 작업**: 마이그레이션 실행 → main.py 통합
