-- =============================================================================
-- IMS Crawler Database Setup - Step 5: Views
-- =============================================================================
-- Description: Create views and materialized views for common queries
-- =============================================================================

\c ims_crawler
SET search_path TO ims, public;

-- =============================================================================
-- View 1: User Dashboard - Overall user statistics
-- =============================================================================

CREATE OR REPLACE VIEW ims.v_user_dashboard AS
SELECT
    u.user_id,
    u.username,
    u.full_name,
    u.department,
    u.last_login_at,

    -- Session statistics
    COUNT(DISTINCT cs.session_id) AS total_sessions,
    COUNT(DISTINCT cs.session_id) FILTER (WHERE cs.status = 'completed') AS successful_sessions,
    COUNT(DISTINCT cs.session_id) FILTER (WHERE cs.status = 'failed') AS failed_sessions,

    -- Issue statistics
    SUM(cs.issues_crawled) AS total_issues_crawled,
    COUNT(DISTINCT si.issue_pk) AS unique_issues,

    -- Attachment statistics
    SUM(cs.attachments_downloaded) AS total_attachments,

    -- Performance metrics
    AVG(cs.duration_seconds)::INTEGER AS avg_session_duration_sec,
    MAX(cs.started_at) AS last_session_date,

    -- Product usage
    MODE() WITHIN GROUP (ORDER BY cs.product) AS most_used_product,
    COUNT(DISTINCT cs.product) AS products_used

FROM ims.users u
LEFT JOIN ims.crawl_sessions cs ON u.user_id = cs.user_id
LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
WHERE u.is_active = TRUE
GROUP BY u.user_id, u.username, u.full_name, u.department, u.last_login_at;

COMMENT ON VIEW ims.v_user_dashboard IS 'User dashboard with comprehensive statistics';

-- =============================================================================
-- View 2: Session Detail - Detailed session information
-- =============================================================================

CREATE OR REPLACE VIEW ims.v_session_detail AS
SELECT
    cs.session_id,
    cs.session_uuid,
    cs.user_id,
    u.username,

    -- Search configuration
    cs.product,
    cs.original_query,
    cs.parsed_query,
    cs.query_language,
    cs.max_results,

    -- Execution info
    cs.status,
    cs.started_at,
    cs.completed_at,
    cs.duration_seconds,

    -- Results
    cs.total_issues_found,
    cs.issues_crawled,
    cs.attachments_downloaded,
    cs.failed_issues,

    -- Performance
    cs.search_time_ms,
    cs.crawl_time_ms,
    cs.avg_issue_time_ms,

    -- Related data counts
    COUNT(DISTINCT si.issue_pk) AS unique_issues_count,
    COUNT(DISTINCT a.attachment_id) AS attachments_count,
    COUNT(DISTINCT se.error_id) AS errors_count,

    -- Storage path
    cs.data_path

FROM ims.crawl_sessions cs
JOIN ims.users u ON cs.user_id = u.user_id
LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
LEFT JOIN ims.attachments a ON cs.session_id = a.session_id
LEFT JOIN ims.session_errors se ON cs.session_id = se.session_id
GROUP BY
    cs.session_id, cs.session_uuid, cs.user_id, u.username,
    cs.product, cs.original_query, cs.parsed_query, cs.query_language,
    cs.max_results, cs.status, cs.started_at, cs.completed_at,
    cs.duration_seconds, cs.total_issues_found, cs.issues_crawled,
    cs.attachments_downloaded, cs.failed_issues, cs.search_time_ms,
    cs.crawl_time_ms, cs.avg_issue_time_ms, cs.data_path;

COMMENT ON VIEW ims.v_session_detail IS 'Detailed session information with related counts';

-- =============================================================================
-- View 3: Issue Search - Issue information with metadata
-- =============================================================================

CREATE OR REPLACE VIEW ims.v_issue_search AS
SELECT
    i.issue_pk,
    i.issue_id,
    i.title,
    i.description,
    i.product,
    i.status,
    i.priority,
    i.severity,
    i.issue_type,

    -- People
    i.reporter,
    i.owner,
    i.manager,

    -- Dates
    i.registered_date,
    i.modified_date,
    i.closed_date,

    -- Project info
    i.project_code,
    i.project_name,
    i.site,
    i.customer,

    -- Tracking
    i.first_crawled_at,
    i.last_crawled_at,
    i.crawl_count,

    -- Related data counts
    COUNT(DISTINCT ic.comment_id) AS comments_count,
    COUNT(DISTINCT ih.history_id) AS history_count,
    COUNT(DISTINCT a.attachment_id) AS attachments_count,
    COUNT(DISTINCT si.session_id) AS sessions_count

FROM ims.issues i
LEFT JOIN ims.issue_comments ic ON i.issue_pk = ic.issue_pk
LEFT JOIN ims.issue_history ih ON i.issue_pk = ih.issue_pk
LEFT JOIN ims.attachments a ON i.issue_pk = a.issue_pk
LEFT JOIN ims.session_issues si ON i.issue_pk = si.issue_pk
GROUP BY
    i.issue_pk, i.issue_id, i.title, i.description, i.product,
    i.status, i.priority, i.severity, i.issue_type,
    i.reporter, i.owner, i.manager,
    i.registered_date, i.modified_date, i.closed_date,
    i.project_code, i.project_name, i.site, i.customer,
    i.first_crawled_at, i.last_crawled_at, i.crawl_count;

COMMENT ON VIEW ims.v_issue_search IS 'Issue search view with related counts';

-- =============================================================================
-- View 4: Recent Activity - Recent user activity
-- =============================================================================

CREATE OR REPLACE VIEW ims.v_recent_activity AS
SELECT
    al.log_id,
    al.user_id,
    u.username,
    al.action,
    al.resource_type,
    al.resource_id,
    al.created_at,

    -- Session info if applicable
    CASE
        WHEN al.resource_type = 'session' THEN cs.product
        ELSE NULL
    END AS product,

    CASE
        WHEN al.resource_type = 'session' THEN cs.status
        ELSE NULL
    END AS session_status

FROM ims.audit_log al
JOIN ims.users u ON al.user_id = u.user_id
LEFT JOIN ims.crawl_sessions cs ON
    al.resource_type = 'session' AND
    al.resource_id = cs.session_uuid::VARCHAR
ORDER BY al.created_at DESC
LIMIT 1000;

COMMENT ON VIEW ims.v_recent_activity IS 'Recent user activity from audit log';

-- =============================================================================
-- View 5: Product Statistics - Statistics by product
-- =============================================================================

CREATE OR REPLACE VIEW ims.v_product_stats AS
SELECT
    cs.product,

    -- Session counts
    COUNT(DISTINCT cs.session_id) AS total_sessions,
    COUNT(DISTINCT cs.session_id) FILTER (WHERE cs.status = 'completed') AS successful_sessions,

    -- Issue counts
    SUM(cs.issues_crawled) AS total_issues_crawled,
    COUNT(DISTINCT si.issue_pk) AS unique_issues,

    -- Performance
    AVG(cs.duration_seconds)::INTEGER AS avg_session_duration_sec,
    AVG(cs.avg_issue_time_ms)::INTEGER AS avg_issue_time_ms,

    -- User counts
    COUNT(DISTINCT cs.user_id) AS unique_users,

    -- Time range
    MIN(cs.started_at) AS first_session,
    MAX(cs.started_at) AS last_session

FROM ims.crawl_sessions cs
LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
GROUP BY cs.product
ORDER BY total_sessions DESC;

COMMENT ON VIEW ims.v_product_stats IS 'Statistics grouped by product';

-- =============================================================================
-- Materialized View 1: Daily Session Summary
-- =============================================================================

CREATE MATERIALIZED VIEW ims.mv_daily_session_summary AS
SELECT
    DATE(cs.started_at) AS session_date,
    cs.product,
    cs.user_id,
    u.username,

    -- Session counts
    COUNT(*) AS sessions_count,
    COUNT(*) FILTER (WHERE cs.status = 'completed') AS completed_count,
    COUNT(*) FILTER (WHERE cs.status = 'failed') AS failed_count,

    -- Issue counts
    SUM(cs.issues_crawled) AS total_issues,
    AVG(cs.issues_crawled)::NUMERIC(10,2) AS avg_issues_per_session,

    -- Performance
    AVG(cs.duration_seconds)::INTEGER AS avg_duration_sec,
    SUM(cs.duration_seconds) AS total_duration_sec

FROM ims.crawl_sessions cs
JOIN ims.users u ON cs.user_id = u.user_id
GROUP BY DATE(cs.started_at), cs.product, cs.user_id, u.username;

CREATE UNIQUE INDEX idx_mv_daily_summary_unique ON ims.mv_daily_session_summary(session_date, product, user_id);
CREATE INDEX idx_mv_daily_summary_date ON ims.mv_daily_session_summary(session_date DESC);

COMMENT ON MATERIALIZED VIEW ims.mv_daily_session_summary IS 'Daily session summary (refresh daily)';

-- =============================================================================
-- Materialized View 2: Issue Trend Analysis
-- =============================================================================

CREATE MATERIALIZED VIEW ims.mv_issue_trends AS
SELECT
    i.product,
    i.status,
    i.priority,
    DATE_TRUNC('week', i.registered_date) AS week_start,

    -- Counts
    COUNT(*) AS issue_count,
    COUNT(*) FILTER (WHERE i.closed_date IS NOT NULL) AS closed_count,

    -- Time metrics
    AVG(EXTRACT(EPOCH FROM (i.closed_date - i.registered_date))/86400)::NUMERIC(10,2) AS avg_days_to_close,

    -- Crawl statistics
    AVG(i.crawl_count)::NUMERIC(10,2) AS avg_crawl_count,
    MAX(i.last_crawled_at) AS last_crawled

FROM ims.issues i
WHERE i.registered_date IS NOT NULL
GROUP BY i.product, i.status, i.priority, DATE_TRUNC('week', i.registered_date);

CREATE INDEX idx_mv_issue_trends_product ON ims.mv_issue_trends(product);
CREATE INDEX idx_mv_issue_trends_week ON ims.mv_issue_trends(week_start DESC);

COMMENT ON MATERIALIZED VIEW ims.mv_issue_trends IS 'Weekly issue trend analysis';

-- =============================================================================
-- Materialized View Refresh Function
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ims.mv_daily_session_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY ims.mv_issue_trends;

    RAISE NOTICE 'Materialized views refreshed at %', CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ims.refresh_materialized_views() IS 'Refresh all materialized views concurrently';

-- =============================================================================
-- Success message
-- =============================================================================

DO $$
DECLARE
    view_count INTEGER;
    mv_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO view_count
    FROM pg_views
    WHERE schemaname = 'ims';

    SELECT COUNT(*) INTO mv_count
    FROM pg_matviews
    WHERE schemaname = 'ims';

    RAISE NOTICE '✅ Views created successfully!';
    RAISE NOTICE 'Regular views: %, Materialized views: %', view_count, mv_count;
    RAISE NOTICE 'Next step: Run 06_create_roles.sql';
END $$;
