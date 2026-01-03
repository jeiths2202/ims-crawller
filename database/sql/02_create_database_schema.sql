-- =============================================================================
-- IMS Crawler Database Setup - Step 2: Database and Schema
-- =============================================================================
-- Description: Create database, schema, and all tables
-- =============================================================================

-- Connect to postgres database first, then create new database
-- \c postgres

-- Create database
CREATE DATABASE ims_crawler
    WITH
    OWNER = raguser
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

COMMENT ON DATABASE ims_crawler IS 'IMS Crawler metadata and analytics database';

-- Connect to new database
\c ims_crawler

-- Create schema
CREATE SCHEMA IF NOT EXISTS ims;

COMMENT ON SCHEMA ims IS 'IMS Crawler main schema';

-- Set search path
SET search_path TO ims, public;

-- =============================================================================
-- Table 1: users
-- =============================================================================

CREATE TABLE ims.users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    full_name VARCHAR(200),
    department VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('admin', 'user', 'readonly')),
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

COMMENT ON TABLE ims.users IS '사용자 정보';
COMMENT ON COLUMN ims.users.preferences IS '사용자 설정 (JSON: crawler_config, ui_preferences)';

-- =============================================================================
-- Table 2: crawl_sessions
-- =============================================================================

CREATE TABLE ims.crawl_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    session_uuid VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES ims.users(user_id) ON DELETE CASCADE,

    -- Search configuration
    product VARCHAR(100) NOT NULL,
    original_query TEXT NOT NULL,
    parsed_query TEXT NOT NULL,
    query_language VARCHAR(10) DEFAULT 'en',
    max_results INTEGER DEFAULT 100,
    crawl_related BOOLEAN DEFAULT FALSE,

    -- Execution info
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
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
    parallel_workers INTEGER DEFAULT 1,

    -- Storage
    data_path TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ims.crawl_sessions IS '크롤링 세션 정보';

-- =============================================================================
-- Table 3: issues
-- =============================================================================

CREATE TABLE ims.issues (
    issue_pk BIGSERIAL PRIMARY KEY,
    issue_id VARCHAR(50) UNIQUE NOT NULL,

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
    full_data JSONB,

    -- Tracking
    first_crawled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_crawled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    crawl_count INTEGER DEFAULT 1,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ims.issues IS 'IMS 이슈 정보';

-- =============================================================================
-- Table 4: session_issues (Many-to-Many mapping)
-- =============================================================================

CREATE TABLE ims.session_issues (
    session_issue_id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES ims.crawl_sessions(session_id) ON DELETE CASCADE,
    issue_pk BIGINT NOT NULL REFERENCES ims.issues(issue_pk) ON DELETE CASCADE,

    crawl_order INTEGER,
    crawl_duration_ms INTEGER,
    had_errors BOOLEAN DEFAULT FALSE,
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(session_id, issue_pk)
);

COMMENT ON TABLE ims.session_issues IS '세션별 크롤링된 이슈 매핑';

-- =============================================================================
-- Table 5: issue_comments
-- =============================================================================

CREATE TABLE ims.issue_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    issue_pk BIGINT NOT NULL REFERENCES ims.issues(issue_pk) ON DELETE CASCADE,

    comment_number INTEGER,
    author VARCHAR(100),
    content TEXT,
    commented_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ims.issue_comments IS '이슈 코멘트';

-- =============================================================================
-- Table 6: issue_history
-- =============================================================================

CREATE TABLE ims.issue_history (
    history_id BIGSERIAL PRIMARY KEY,
    issue_pk BIGINT NOT NULL REFERENCES ims.issues(issue_pk) ON DELETE CASCADE,

    changed_by VARCHAR(100),
    changed_at TIMESTAMPTZ,
    change_type VARCHAR(50),
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    description TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ims.issue_history IS '이슈 변경 이력';

-- =============================================================================
-- Table 7: attachments
-- =============================================================================

CREATE TABLE ims.attachments (
    attachment_id BIGSERIAL PRIMARY KEY,
    issue_pk BIGINT NOT NULL REFERENCES ims.issues(issue_pk) ON DELETE CASCADE,
    session_id BIGINT REFERENCES ims.crawl_sessions(session_id) ON DELETE SET NULL,

    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(100),
    file_size BIGINT,
    file_path TEXT,

    download_url TEXT,
    downloaded BOOLEAN DEFAULT FALSE,
    download_error TEXT,

    -- Text extraction for RAG
    extracted_text TEXT,
    text_extracted BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ims.attachments IS '첨부파일 정보';

-- =============================================================================
-- Table 8: search_queries
-- =============================================================================

CREATE TABLE ims.search_queries (
    query_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES ims.users(user_id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES ims.crawl_sessions(session_id) ON DELETE CASCADE,

    original_query TEXT NOT NULL,
    parsed_query TEXT,
    query_language VARCHAR(10),

    product VARCHAR(100),
    results_count INTEGER,

    -- NL parsing info
    parsing_method VARCHAR(50),
    parsing_confidence NUMERIC(5,2),
    synonym_expanded BOOLEAN DEFAULT FALSE,
    intent_filtered BOOLEAN DEFAULT FALSE,

    queried_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ims.search_queries IS '검색 쿼리 이력';

-- =============================================================================
-- Table 9: session_errors
-- =============================================================================

CREATE TABLE ims.session_errors (
    error_id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES ims.crawl_sessions(session_id) ON DELETE CASCADE,

    error_type VARCHAR(50),
    severity VARCHAR(20) CHECK (severity IN ('error', 'warning', 'info')),
    error_message TEXT,
    error_detail JSONB,

    occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ims.session_errors IS '세션 에러 및 경고 로그';

-- =============================================================================
-- Table 10: analytics_daily
-- =============================================================================

CREATE TABLE ims.analytics_daily (
    stat_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES ims.users(user_id) ON DELETE CASCADE,
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
    product_stats JSONB DEFAULT '{}',

    -- Top queries
    top_queries JSONB DEFAULT '[]',

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, stat_date)
);

COMMENT ON TABLE ims.analytics_daily IS '일별 통계 정보';

-- =============================================================================
-- Table 11: analytics_monthly
-- =============================================================================

CREATE TABLE ims.analytics_monthly (
    stat_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES ims.users(user_id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),

    -- Session stats
    total_sessions INTEGER DEFAULT 0,
    avg_sessions_per_day NUMERIC(10,2),

    -- Issue stats
    total_issues_crawled INTEGER DEFAULT 0,
    unique_issues INTEGER DEFAULT 0,

    -- Trends
    keyword_trends JSONB DEFAULT '{}',
    product_distribution JSONB DEFAULT '{}',
    issue_status_breakdown JSONB DEFAULT '{}',

    -- Quality metrics
    avg_parsing_confidence NUMERIC(5,2),
    synonym_expansion_rate NUMERIC(5,2),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, year, month)
);

COMMENT ON TABLE ims.analytics_monthly IS '월별 통계 및 트렌드 분석';

-- =============================================================================
-- Table 12: audit_log
-- =============================================================================

CREATE TABLE ims.audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES ims.users(user_id) ON DELETE SET NULL,

    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),

    old_value JSONB,
    new_value JSONB,

    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ims.audit_log IS '감사 로그 (모든 중요 작업 추적)';

-- =============================================================================
-- Success message
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Database schema created successfully!';
    RAISE NOTICE 'Total tables created: 12';
    RAISE NOTICE 'Next step: Run 03_create_indexes.sql';
END $$;
