# IMS Crawler PostgreSQL Database Schema Design

## 📋 설계 개요

**목적**: IMS Crawler 메타데이터를 PostgreSQL에서 중앙 집중식으로 관리

**핵심 원칙**:
1. **정규화**: 데이터 중복 최소화, 무결성 보장
2. **성능**: 인덱스 최적화, 쿼리 성능 고려
3. **확장성**: 대용량 데이터 처리 가능
4. **이력 관리**: 모든 변경 이력 추적
5. **파티셔닝**: 시간 기반 파티션으로 성능 최적화

## 🏗️ 데이터베이스 구조

```
Database: ims_crawler
├── Tablespace: ims_metadata_tbs (SSD 권장)
├── Schema: ims
│   ├── users                    # 사용자 정보
│   ├── crawl_sessions          # 크롤링 세션
│   ├── issues                  # 이슈 정보
│   ├── issue_comments          # 이슈 코멘트
│   ├── issue_history           # 이슈 변경 이력
│   ├── attachments             # 첨부파일 정보
│   ├── search_queries          # 검색 쿼리 이력
│   ├── session_errors          # 세션 에러 로그
│   ├── analytics_daily         # 일별 통계
│   ├── analytics_monthly       # 월별 통계
│   └── audit_log               # 감사 로그
```

## 📊 테이블 스키마

### 1. users (사용자)

```sql
CREATE TABLE ims.users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    full_name VARCHAR(200),
    department VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

CREATE INDEX idx_users_username ON ims.users(username);
CREATE INDEX idx_users_is_active ON ims.users(is_active);

COMMENT ON TABLE ims.users IS '사용자 정보';
COMMENT ON COLUMN ims.users.preferences IS '사용자 설정 (JSON: crawler_config, ui_preferences, etc.)';
```

### 2. crawl_sessions (크롤링 세션)

```sql
CREATE TABLE ims.crawl_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    session_uuid VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES ims.users(user_id),

    -- Search configuration
    product VARCHAR(100) NOT NULL,
    original_query TEXT NOT NULL,
    parsed_query TEXT NOT NULL,
    query_language VARCHAR(10),
    max_results INTEGER,
    crawl_related BOOLEAN DEFAULT FALSE,

    -- Execution info
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed, cancelled
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,

    -- Results summary
    total_issues_found INTEGER DEFAULT 0,
    issues_crawled INTEGER DEFAULT 0,
    attachments_downloaded INTEGER DEFAULT 0,
    failed_issues INTEGER DEFAULT 0,
    related_issues INTEGER DEFAULT 0,

    -- Performance metrics
    search_time_ms INTEGER,
    crawl_time_ms INTEGER,
    avg_issue_time_ms INTEGER,
    parallel_workers INTEGER,

    -- Storage
    data_path TEXT,  -- Path to JSON files

    -- Metadata
    metadata JSONB,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Partitioning by month for performance
CREATE TABLE ims.crawl_sessions_2026_01 PARTITION OF ims.crawl_sessions
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE INDEX idx_sessions_user_id ON ims.crawl_sessions(user_id);
CREATE INDEX idx_sessions_product ON ims.crawl_sessions(product);
CREATE INDEX idx_sessions_status ON ims.crawl_sessions(status);
CREATE INDEX idx_sessions_started_at ON ims.crawl_sessions(started_at DESC);
CREATE INDEX idx_sessions_uuid ON ims.crawl_sessions(session_uuid);
CREATE INDEX idx_sessions_metadata ON ims.crawl_sessions USING GIN(metadata);

COMMENT ON TABLE ims.crawl_sessions IS '크롤링 세션 정보';
```

### 3. issues (이슈)

```sql
CREATE TABLE ims.issues (
    issue_pk BIGSERIAL PRIMARY KEY,
    issue_id VARCHAR(50) UNIQUE NOT NULL,  -- IMS issue ID

    -- Basic info
    title TEXT NOT NULL,
    description TEXT,
    product VARCHAR(100),
    status VARCHAR(50),
    priority VARCHAR(20),
    severity VARCHAR(20),
    issue_type VARCHAR(50),

    -- People
    reporter VARCHAR(100),
    owner VARCHAR(100),
    manager VARCHAR(100),

    -- Dates
    registered_date TIMESTAMPTZ,
    modified_date TIMESTAMPTZ,
    closed_date TIMESTAMPTZ,

    -- Project info
    project_code VARCHAR(100),
    project_name VARCHAR(200),
    site VARCHAR(100),
    customer VARCHAR(200),

    -- Version info
    found_version VARCHAR(100),
    fixed_version VARCHAR(100),
    target_version VARCHAR(100),

    -- Full data
    full_data JSONB,  -- Complete JSON from crawler

    -- Tracking
    first_crawled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_crawled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    crawl_count INTEGER DEFAULT 1,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_issues_issue_id ON ims.issues(issue_id);
CREATE INDEX idx_issues_product ON ims.issues(product);
CREATE INDEX idx_issues_status ON ims.issues(status);
CREATE INDEX idx_issues_priority ON ims.issues(priority);
CREATE INDEX idx_issues_registered_date ON ims.issues(registered_date DESC);
CREATE INDEX idx_issues_title_fts ON ims.issues USING GIN(to_tsvector('english', title));
CREATE INDEX idx_issues_description_fts ON ims.issues USING GIN(to_tsvector('english', description));
CREATE INDEX idx_issues_full_data ON ims.issues USING GIN(full_data);

COMMENT ON TABLE ims.issues IS 'IMS 이슈 정보';
```

### 4. session_issues (세션-이슈 매핑)

```sql
CREATE TABLE ims.session_issues (
    session_issue_id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES ims.crawl_sessions(session_id) ON DELETE CASCADE,
    issue_pk BIGINT NOT NULL REFERENCES ims.issues(issue_pk) ON DELETE CASCADE,

    -- Crawl info for this specific session
    crawl_order INTEGER,  -- Order in which it was crawled
    crawl_duration_ms INTEGER,
    had_errors BOOLEAN DEFAULT FALSE,
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(session_id, issue_pk)
);

CREATE INDEX idx_session_issues_session_id ON ims.session_issues(session_id);
CREATE INDEX idx_session_issues_issue_pk ON ims.session_issues(issue_pk);

COMMENT ON TABLE ims.session_issues IS '세션별 크롤링된 이슈 매핑';
```

### 5. issue_comments (이슈 코멘트)

```sql
CREATE TABLE ims.issue_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    issue_pk BIGINT NOT NULL REFERENCES ims.issues(issue_pk) ON DELETE CASCADE,

    comment_number INTEGER,
    author VARCHAR(100),
    content TEXT,
    commented_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_comments_issue_pk ON ims.issue_comments(issue_pk);
CREATE INDEX idx_comments_author ON ims.issue_comments(author);
CREATE INDEX idx_comments_commented_at ON ims.issue_comments(commented_at DESC);

COMMENT ON TABLE ims.issue_comments IS '이슈 코멘트';
```

### 6. issue_history (이슈 변경 이력)

```sql
CREATE TABLE ims.issue_history (
    history_id BIGSERIAL PRIMARY KEY,
    issue_pk BIGINT NOT NULL REFERENCES ims.issues(issue_pk) ON DELETE CASCADE,

    changed_by VARCHAR(100),
    changed_at TIMESTAMPTZ,
    change_type VARCHAR(50),  -- status_change, assignment, update, etc.
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    description TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_history_issue_pk ON ims.issue_history(issue_pk);
CREATE INDEX idx_history_changed_at ON ims.issue_history(changed_at DESC);
CREATE INDEX idx_history_change_type ON ims.issue_history(change_type);

COMMENT ON TABLE ims.issue_history IS '이슈 변경 이력';
```

### 7. attachments (첨부파일)

```sql
CREATE TABLE ims.attachments (
    attachment_id BIGSERIAL PRIMARY KEY,
    issue_pk BIGINT NOT NULL REFERENCES ims.issues(issue_pk) ON DELETE CASCADE,
    session_id BIGINT REFERENCES ims.crawl_sessions(session_id) ON DELETE SET NULL,

    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(100),
    file_size BIGINT,  -- bytes
    file_path TEXT,  -- Local storage path

    download_url TEXT,
    downloaded BOOLEAN DEFAULT FALSE,
    download_error TEXT,

    -- Text extraction for RAG
    extracted_text TEXT,
    text_extracted BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attachments_issue_pk ON ims.attachments(issue_pk);
CREATE INDEX idx_attachments_session_id ON ims.attachments(session_id);
CREATE INDEX idx_attachments_file_type ON ims.attachments(file_type);
CREATE INDEX idx_attachments_downloaded ON ims.attachments(downloaded);
CREATE INDEX idx_attachments_text_fts ON ims.attachments USING GIN(to_tsvector('english', extracted_text));

COMMENT ON TABLE ims.attachments IS '첨부파일 정보';
```

### 8. search_queries (검색 쿼리 이력)

```sql
CREATE TABLE ims.search_queries (
    query_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES ims.users(user_id),
    session_id BIGINT REFERENCES ims.crawl_sessions(session_id) ON DELETE CASCADE,

    original_query TEXT NOT NULL,
    parsed_query TEXT,
    query_language VARCHAR(10),

    product VARCHAR(100),
    results_count INTEGER,

    -- NL parsing info
    parsing_method VARCHAR(50),  -- rules, llm, hybrid
    parsing_confidence NUMERIC(5,2),
    synonym_expanded BOOLEAN DEFAULT FALSE,
    intent_filtered BOOLEAN DEFAULT FALSE,

    queried_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_queries_user_id ON ims.search_queries(user_id);
CREATE INDEX idx_queries_product ON ims.search_queries(product);
CREATE INDEX idx_queries_queried_at ON ims.search_queries(queried_at DESC);
CREATE INDEX idx_queries_original_fts ON ims.search_queries USING GIN(to_tsvector('english', original_query));

COMMENT ON TABLE ims.search_queries IS '검색 쿼리 이력';
```

### 9. session_errors (세션 에러 로그)

```sql
CREATE TABLE ims.session_errors (
    error_id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES ims.crawl_sessions(session_id) ON DELETE CASCADE,

    error_type VARCHAR(50),  -- authentication, parsing, crawling, network
    severity VARCHAR(20),  -- error, warning, info
    error_message TEXT,
    error_detail JSONB,

    occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_errors_session_id ON ims.session_errors(session_id);
CREATE INDEX idx_errors_error_type ON ims.session_errors(error_type);
CREATE INDEX idx_errors_severity ON ims.session_errors(severity);
CREATE INDEX idx_errors_occurred_at ON ims.session_errors(occurred_at DESC);

COMMENT ON TABLE ims.session_errors IS '세션 에러 및 경고 로그';
```

### 10. analytics_daily (일별 통계)

```sql
CREATE TABLE ims.analytics_daily (
    stat_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES ims.users(user_id),
    stat_date DATE NOT NULL,

    -- Session stats
    sessions_count INTEGER DEFAULT 0,
    successful_sessions INTEGER DEFAULT 0,
    failed_sessions INTEGER DEFAULT 0,

    -- Issue stats
    issues_crawled INTEGER DEFAULT 0,
    unique_issues INTEGER DEFAULT 0,
    new_issues INTEGER DEFAULT 0,

    -- Attachment stats
    attachments_downloaded INTEGER DEFAULT 0,

    -- Performance stats
    avg_session_duration_sec INTEGER,
    avg_issues_per_session NUMERIC(10,2),

    -- Product breakdown
    product_stats JSONB,  -- {"OpenFrame": 10, "Tibero": 5}

    -- Top queries
    top_queries JSONB,  -- Array of popular queries

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, stat_date)
);

CREATE INDEX idx_analytics_daily_user_id ON ims.analytics_daily(user_id);
CREATE INDEX idx_analytics_daily_stat_date ON ims.analytics_daily(stat_date DESC);

COMMENT ON TABLE ims.analytics_daily IS '일별 통계 정보';
```

### 11. analytics_monthly (월별 통계)

```sql
CREATE TABLE ims.analytics_monthly (
    stat_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES ims.users(user_id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,

    -- Session stats
    total_sessions INTEGER DEFAULT 0,
    avg_sessions_per_day NUMERIC(10,2),

    -- Issue stats
    total_issues_crawled INTEGER DEFAULT 0,
    unique_issues INTEGER DEFAULT 0,

    -- Trends
    keyword_trends JSONB,
    product_distribution JSONB,
    issue_status_breakdown JSONB,

    -- Quality metrics
    avg_parsing_confidence NUMERIC(5,2),
    synonym_expansion_rate NUMERIC(5,2),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, year, month)
);

CREATE INDEX idx_analytics_monthly_user_id ON ims.analytics_monthly(user_id);
CREATE INDEX idx_analytics_monthly_year_month ON ims.analytics_monthly(year, month);

COMMENT ON TABLE ims.analytics_monthly IS '월별 통계 및 트렌드 분석';
```

### 12. audit_log (감사 로그)

```sql
CREATE TABLE ims.audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES ims.users(user_id),

    action VARCHAR(100) NOT NULL,  -- create_session, delete_session, update_config, etc.
    resource_type VARCHAR(50),  -- session, issue, user, etc.
    resource_id VARCHAR(100),

    old_value JSONB,
    new_value JSONB,

    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_id ON ims.audit_log(user_id);
CREATE INDEX idx_audit_action ON ims.audit_log(action);
CREATE INDEX idx_audit_resource_type ON ims.audit_log(resource_type);
CREATE INDEX idx_audit_created_at ON ims.audit_log(created_at DESC);

COMMENT ON TABLE ims.audit_log IS '감사 로그 (모든 중요 작업 추적)';
```

## 🔗 관계도 (ERD)

```
users (1) ──────┬──────> (N) crawl_sessions
                │
                ├──────> (N) search_queries
                │
                ├──────> (N) analytics_daily
                │
                ├──────> (N) analytics_monthly
                │
                └──────> (N) audit_log

crawl_sessions (1) ───┬─> (N) session_issues
                      │
                      ├─> (N) session_errors
                      │
                      └─> (N) search_queries

issues (1) ──────────┬──> (N) session_issues
                     │
                     ├──> (N) issue_comments
                     │
                     ├──> (N) issue_history
                     │
                     └──> (N) attachments
```

## 📐 인덱스 전략

### 1. 기본 인덱스
- 모든 Primary Key (자동 생성)
- 모든 Foreign Key
- UNIQUE 제약조건 컬럼

### 2. 성능 인덱스
- 자주 조회되는 컬럼 (user_id, product, status, date)
- 정렬에 사용되는 컬럼 (created_at DESC)
- WHERE 절에 자주 사용되는 컬럼

### 3. 전문 검색 인덱스 (GIN)
- title, description (이슈 텍스트 검색)
- extracted_text (첨부파일 내용 검색)
- original_query (검색 쿼리 분석)

### 4. JSON 인덱스 (GIN)
- metadata, full_data (JSONB 컬럼)
- 특정 JSON 경로에 대한 인덱스

## 🔐 보안 및 권한

```sql
-- Role 정의
CREATE ROLE ims_admin;
CREATE ROLE ims_user;
CREATE ROLE ims_readonly;

-- ims_admin: 모든 권한
GRANT ALL ON SCHEMA ims TO ims_admin;
GRANT ALL ON ALL TABLES IN SCHEMA ims TO ims_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA ims TO ims_admin;

-- ims_user: 읽기 + 자신의 데이터 쓰기
GRANT USAGE ON SCHEMA ims TO ims_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ims TO ims_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ims TO ims_user;

-- ims_readonly: 읽기만
GRANT USAGE ON SCHEMA ims TO ims_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA ims TO ims_readonly;

-- Row Level Security (RLS) 예시
ALTER TABLE ims.crawl_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_sessions_policy ON ims.crawl_sessions
    FOR ALL
    TO ims_user
    USING (user_id = current_setting('app.current_user_id')::INTEGER);
```

## 📦 파티셔닝 전략

### 1. crawl_sessions - 월별 파티션

```sql
-- 자동 파티션 생성 함수
CREATE OR REPLACE FUNCTION ims.create_monthly_partition()
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    start_date := DATE_TRUNC('month', CURRENT_DATE);
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'crawl_sessions_' || TO_CHAR(start_date, 'YYYY_MM');

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS ims.%I PARTITION OF ims.crawl_sessions
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;

-- 매월 1일 자동 실행
SELECT cron.schedule('create-monthly-partition', '0 0 1 * *',
    $$SELECT ims.create_monthly_partition()$$
);
```

### 2. audit_log - 분기별 파티션

```sql
-- 오래된 로그는 별도 테이블로 아카이빙
CREATE TABLE ims.audit_log_archive (LIKE ims.audit_log INCLUDING ALL);
```

## 🔄 트리거 및 자동화

### 1. updated_at 자동 갱신

```sql
CREATE OR REPLACE FUNCTION ims.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON ims.users
    FOR EACH ROW
    EXECUTE FUNCTION ims.update_updated_at();

-- 모든 테이블에 동일하게 적용
```

### 2. 일별 통계 자동 집계

```sql
CREATE OR REPLACE FUNCTION ims.aggregate_daily_stats()
RETURNS void AS $$
BEGIN
    INSERT INTO ims.analytics_daily (
        user_id, stat_date, sessions_count, issues_crawled, unique_issues
    )
    SELECT
        user_id,
        DATE(started_at) AS stat_date,
        COUNT(*) AS sessions_count,
        SUM(issues_crawled) AS issues_crawled,
        COUNT(DISTINCT issue_pk) AS unique_issues
    FROM ims.crawl_sessions cs
    LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
    WHERE DATE(started_at) = CURRENT_DATE - INTERVAL '1 day'
    GROUP BY user_id, DATE(started_at)
    ON CONFLICT (user_id, stat_date)
    DO UPDATE SET
        sessions_count = EXCLUDED.sessions_count,
        issues_crawled = EXCLUDED.issues_crawled,
        unique_issues = EXCLUDED.unique_issues;
END;
$$ LANGUAGE plpgsql;

-- 매일 자정에 실행
```

### 3. 이슈 중복 체크 및 업데이트

```sql
CREATE OR REPLACE FUNCTION ims.upsert_issue()
RETURNS TRIGGER AS $$
BEGIN
    -- 기존 이슈가 있으면 업데이트
    UPDATE ims.issues
    SET
        title = NEW.title,
        description = NEW.description,
        status = NEW.status,
        modified_date = NEW.modified_date,
        full_data = NEW.full_data,
        last_crawled_at = CURRENT_TIMESTAMP,
        crawl_count = crawl_count + 1
    WHERE issue_id = NEW.issue_id;

    -- 없으면 삽입 (RETURNING으로 처리)
    IF NOT FOUND THEN
        RETURN NEW;
    ELSE
        RETURN NULL;  -- UPDATE만 수행, INSERT 스킵
    END IF;
END;
$$ LANGUAGE plpgsql;
```

## 📊 뷰 (Views)

### 1. 사용자 대시보드 뷰

```sql
CREATE VIEW ims.v_user_dashboard AS
SELECT
    u.user_id,
    u.username,
    COUNT(DISTINCT cs.session_id) AS total_sessions,
    COUNT(DISTINCT si.issue_pk) AS unique_issues,
    SUM(cs.issues_crawled) AS total_issues_crawled,
    MAX(cs.started_at) AS last_session_at,
    AVG(cs.duration_seconds) AS avg_session_duration
FROM ims.users u
LEFT JOIN ims.crawl_sessions cs ON u.user_id = cs.user_id
LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
GROUP BY u.user_id, u.username;
```

### 2. 세션 상세 뷰

```sql
CREATE VIEW ims.v_session_detail AS
SELECT
    cs.session_id,
    cs.session_uuid,
    u.username,
    cs.product,
    cs.original_query,
    cs.status,
    cs.started_at,
    cs.completed_at,
    cs.duration_seconds,
    cs.issues_crawled,
    COUNT(si.issue_pk) AS actual_issue_count,
    ARRAY_AGG(i.issue_id ORDER BY si.crawl_order) AS issue_ids
FROM ims.crawl_sessions cs
JOIN ims.users u ON cs.user_id = u.user_id
LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
LEFT JOIN ims.issues i ON si.issue_pk = i.issue_pk
GROUP BY cs.session_id, u.username;
```

### 3. 이슈 검색 뷰

```sql
CREATE VIEW ims.v_issue_search AS
SELECT
    i.issue_pk,
    i.issue_id,
    i.title,
    i.description,
    i.product,
    i.status,
    i.priority,
    i.registered_date,
    i.last_crawled_at,
    COUNT(DISTINCT si.session_id) AS crawled_in_sessions,
    COUNT(DISTINCT a.attachment_id) AS attachment_count,
    COUNT(DISTINCT ic.comment_id) AS comment_count
FROM ims.issues i
LEFT JOIN ims.session_issues si ON i.issue_pk = si.issue_pk
LEFT JOIN ims.attachments a ON i.issue_pk = a.issue_pk
LEFT JOIN ims.issue_comments ic ON i.issue_pk = ic.issue_pk
GROUP BY i.issue_pk;
```

---

**다음 단계**: SQL 스크립트 생성 및 Python ORM 모델 정의
