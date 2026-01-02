# 프로젝트 계획

## 개요
사내 IMS(Issue Management System)를 크롤링하고 LLM과 연동하여 최종적으로 지식을 제공하는 서비스 구현

## 개발 단계

### ✅ 1차 완료: Python CLI 핵심 기능 구현

**구현된 기능:**
- ✅ Playwright 기반 웹 크롤링 엔진
- ✅ IMS 로그인 및 세션 관리
- ✅ IMS 검색 문법 지원 (OR/AND/정확한 구문)
- ✅ 이슈 상세 정보 추출 (제목, 설명, 댓글, 히스토리)
- ✅ 첨부파일 다운로드 및 텍스트 추출 (PDF, Word, 이미지)
- ✅ JSON 형식으로 구조화된 데이터 출력
- ✅ Rich CLI 인터페이스

**기술 스택:**
- Python 3.10+
- Playwright (브라우저 자동화)
- BeautifulSoup4 (HTML 파싱)
- Click + Rich (CLI)
- PyPDF2, pdfplumber (문서 처리)

### 🔜 2차 계획: 웹 애플리케이션 확장

**예정된 기능:**
- 웹 UI (Flask/FastAPI + React/Vue)
- 실시간 크롤링 진행 상황 대시보드
- 스케줄링 기능 (주기적 크롤링)
- 데이터베이스 저장 (PostgreSQL)
- 다중 사용자 지원

## 주요 기능

### 현재 구현됨
1. **IMS 데이터 크롤링**
   - 제품 및 키워드 기반 검색
   - 사용자 요청 시 실행 (온디맨드)
   - 수십만 건의 이슈 처리 가능
   - 증분 크롤링 지원 (검색 결과 기반)

2. **데이터 추출**
   - 이슈 설명, 댓글, 첨부파일, 히스토리
   - 첨부파일에서 텍스트 자동 추출
   - 구조화된 JSON 출력

3. **검색 문법 지원**
   - OR 검색: 공백 구분 (예: "Tmax Tibero")
   - AND 검색: + 연산자 (예: "error +timeout")
   - 정확한 구문: 따옴표 (예: '"connection timeout"')
   - 복합 검색: 모든 연산자 조합

### 향후 구현 예정
4. **RAG 연동**
   - Vector DB 통합 (Chroma/Qdrant/Pinecone)
   - 기존 vLLM 기반 RAG 시스템 연동
   - Graph DB 활용

5. **지식 검색/제공**
   - LLM 기반 트러블슈팅 가이드
   - 유사 이슈 검색
   - 해결 패턴 요약

## 기술 스택

### 현재 (1차)
- **언어**: Python 3.10+
- **웹 자동화**: Playwright
- **HTML 파싱**: BeautifulSoup4
- **CLI**: Click + Rich
- **문서 처리**: PyPDF2, pdfplumber, python-docx
- **설정 관리**: python-dotenv

### 예정 (2차)
- **웹 프레임워크**: Flask/FastAPI
- **프론트엔드**: React/Vue
- **데이터베이스**: PostgreSQL
- **Vector DB**: Chroma/Qdrant/Pinecone
- **LLM**: 기존 vLLM 서버 연동

## 사용 방법

### 설치
```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# .env 파일에 IMS 인증 정보 설정
```

### 실행
```bash
# 설정 확인
python main.py config

# 이슈 크롤링
python main.py crawl --product "Tibero" --keywords "connection +error" --max-results 50

# 검색 쿼리 테스트
python main.py test-query "error +timeout"
```

## 다음 단계

1. **IMS 시스템에 맞춰 커스터마이징**
   - `crawler/auth.py`: 로그인 페이지 셀렉터 업데이트
   - `crawler/ims_scraper.py`: 검색 페이지 구조에 맞게 수정
   - `crawler/parser.py`: 이슈 상세 페이지 파싱 로직 조정

2. **테스트 및 검증**
   - 소량의 이슈로 테스트 (--max-results 10)
   - 브라우저 표시 모드로 디버깅 (--no-headless)

3. **RAG 시스템 연동 준비**
   - JSON 출력을 Vector DB에 로드
   - 임베딩 생성 및 저장
   - LLM 쿼리 인터페이스 구축

## 참고 사항

- 크롤링된 데이터는 `data/issues/` 디렉토리에 JSON 형식으로 저장
- 첨부파일은 `data/attachments/` 디렉토리에 이슈별로 정리
- 모든 TODO 주석은 실제 IMS 시스템에 맞춰 업데이트 필요