-- =============================================================================
-- IMS Crawler Database Setup - Step 4: Functions and Triggers
-- =============================================================================
-- Description: Create stored functions, triggers, and automation
-- =============================================================================

\c ims_crawler
SET search_path TO ims, public;

-- =============================================================================
-- Function 1: Auto-update updated_at timestamp
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ims.update_updated_at() IS 'Automatically update updated_at column on row modification';

-- Apply to all tables with updated_at column
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON ims.users
    FOR EACH ROW
    EXECUTE FUNCTION ims.update_updated_at();

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON ims.crawl_sessions
    FOR EACH ROW
    EXECUTE FUNCTION ims.update_updated_at();

CREATE TRIGGER update_issues_updated_at
    BEFORE UPDATE ON ims.issues
    FOR EACH ROW
    EXECUTE FUNCTION ims.update_updated_at();

-- =============================================================================
-- Function 2: Aggregate daily statistics
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.aggregate_daily_stats(target_date DATE DEFAULT CURRENT_DATE - INTERVAL '1 day')
RETURNS void AS $$
DECLARE
    user_rec RECORD;
BEGIN
    -- Loop through each user
    FOR user_rec IN SELECT user_id FROM ims.users WHERE is_active = TRUE LOOP

        INSERT INTO ims.analytics_daily (
            user_id,
            stat_date,
            sessions_count,
            successful_sessions,
            failed_sessions,
            issues_crawled,
            unique_issues,
            attachments_downloaded,
            avg_session_duration_sec,
            avg_issues_per_session,
            product_stats
        )
        SELECT
            user_rec.user_id,
            target_date,
            COUNT(*) AS sessions_count,
            COUNT(*) FILTER (WHERE status = 'completed') AS successful_sessions,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed_sessions,
            SUM(issues_crawled) AS issues_crawled,
            COUNT(DISTINCT si.issue_pk) AS unique_issues,
            SUM(attachments_downloaded) AS attachments_downloaded,
            AVG(duration_seconds)::INTEGER AS avg_session_duration_sec,
            AVG(issues_crawled)::NUMERIC(10,2) AS avg_issues_per_session,
            jsonb_object_agg(
                COALESCE(product, 'Unknown'),
                product_count
            ) AS product_stats
        FROM ims.crawl_sessions cs
        LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
        LEFT JOIN LATERAL (
            SELECT product, COUNT(*) AS product_count
            FROM ims.crawl_sessions
            WHERE user_id = user_rec.user_id
                AND DATE(started_at) = target_date
            GROUP BY product
        ) products ON TRUE
        WHERE cs.user_id = user_rec.user_id
            AND DATE(cs.started_at) = target_date
        GROUP BY cs.user_id
        HAVING COUNT(*) > 0  -- Only insert if there were sessions

        ON CONFLICT (user_id, stat_date)
        DO UPDATE SET
            sessions_count = EXCLUDED.sessions_count,
            successful_sessions = EXCLUDED.successful_sessions,
            failed_sessions = EXCLUDED.failed_sessions,
            issues_crawled = EXCLUDED.issues_crawled,
            unique_issues = EXCLUDED.unique_issues,
            attachments_downloaded = EXCLUDED.attachments_downloaded,
            avg_session_duration_sec = EXCLUDED.avg_session_duration_sec,
            avg_issues_per_session = EXCLUDED.avg_issues_per_session,
            product_stats = EXCLUDED.product_stats;

    END LOOP;

    RAISE NOTICE 'Daily statistics aggregated for date: %', target_date;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ims.aggregate_daily_stats(DATE) IS 'Aggregate daily statistics for all users';

-- =============================================================================
-- Function 3: Aggregate monthly statistics
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.aggregate_monthly_stats(
    target_year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE),
    target_month INTEGER DEFAULT EXTRACT(MONTH FROM CURRENT_DATE) - 1
)
RETURNS void AS $$
DECLARE
    user_rec RECORD;
    start_date DATE;
    end_date DATE;
BEGIN
    -- Calculate month boundaries
    start_date := DATE_TRUNC('month', MAKE_DATE(target_year, target_month, 1));
    end_date := start_date + INTERVAL '1 month';

    -- Loop through each user
    FOR user_rec IN SELECT user_id FROM ims.users WHERE is_active = TRUE LOOP

        INSERT INTO ims.analytics_monthly (
            user_id,
            year,
            month,
            total_sessions,
            avg_sessions_per_day,
            total_issues_crawled,
            unique_issues,
            avg_parsing_confidence
        )
        SELECT
            user_rec.user_id,
            target_year,
            target_month,
            COUNT(*) AS total_sessions,
            (COUNT(*)::NUMERIC / EXTRACT(DAY FROM end_date - INTERVAL '1 day'))::NUMERIC(10,2) AS avg_sessions_per_day,
            SUM(issues_crawled) AS total_issues_crawled,
            COUNT(DISTINCT si.issue_pk) AS unique_issues,
            AVG(sq.parsing_confidence)::NUMERIC(5,2) AS avg_parsing_confidence
        FROM ims.crawl_sessions cs
        LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
        LEFT JOIN ims.search_queries sq ON cs.session_id = sq.session_id
        WHERE cs.user_id = user_rec.user_id
            AND cs.started_at >= start_date
            AND cs.started_at < end_date
        GROUP BY cs.user_id
        HAVING COUNT(*) > 0

        ON CONFLICT (user_id, year, month)
        DO UPDATE SET
            total_sessions = EXCLUDED.total_sessions,
            avg_sessions_per_day = EXCLUDED.avg_sessions_per_day,
            total_issues_crawled = EXCLUDED.total_issues_crawled,
            unique_issues = EXCLUDED.unique_issues,
            avg_parsing_confidence = EXCLUDED.avg_parsing_confidence;

    END LOOP;

    RAISE NOTICE 'Monthly statistics aggregated for: %-%', target_year, target_month;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ims.aggregate_monthly_stats(INTEGER, INTEGER) IS 'Aggregate monthly statistics for all users';

-- =============================================================================
-- Function 4: Upsert issue (insert or update)
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.upsert_issue(
    p_issue_id VARCHAR(50),
    p_title TEXT,
    p_description TEXT,
    p_product VARCHAR(100),
    p_status VARCHAR(50),
    p_full_data JSONB
)
RETURNS BIGINT AS $$
DECLARE
    v_issue_pk BIGINT;
BEGIN
    INSERT INTO ims.issues (
        issue_id, title, description, product, status, full_data
    ) VALUES (
        p_issue_id, p_title, p_description, p_product, p_status, p_full_data
    )
    ON CONFLICT (issue_id) DO UPDATE SET
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        product = EXCLUDED.product,
        status = EXCLUDED.status,
        full_data = EXCLUDED.full_data,
        modified_date = CURRENT_TIMESTAMP,
        last_crawled_at = CURRENT_TIMESTAMP,
        crawl_count = ims.issues.crawl_count + 1
    RETURNING issue_pk INTO v_issue_pk;

    RETURN v_issue_pk;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ims.upsert_issue IS 'Insert new issue or update existing one';

-- =============================================================================
-- Function 5: Get user statistics
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.get_user_stats(p_user_id INTEGER)
RETURNS TABLE (
    total_sessions BIGINT,
    successful_sessions BIGINT,
    failed_sessions BIGINT,
    total_issues_crawled BIGINT,
    unique_issues BIGINT,
    total_attachments BIGINT,
    avg_session_duration_sec NUMERIC,
    last_session_date TIMESTAMPTZ,
    most_used_product VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) AS total_sessions,
        COUNT(*) FILTER (WHERE status = 'completed') AS successful_sessions,
        COUNT(*) FILTER (WHERE status = 'failed') AS failed_sessions,
        SUM(cs.issues_crawled) AS total_issues_crawled,
        COUNT(DISTINCT si.issue_pk) AS unique_issues,
        SUM(cs.attachments_downloaded) AS total_attachments,
        AVG(cs.duration_seconds)::NUMERIC(10,2) AS avg_session_duration_sec,
        MAX(cs.started_at) AS last_session_date,
        MODE() WITHIN GROUP (ORDER BY cs.product) AS most_used_product
    FROM ims.crawl_sessions cs
    LEFT JOIN ims.session_issues si ON cs.session_id = si.session_id
    WHERE cs.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ims.get_user_stats(INTEGER) IS 'Get comprehensive statistics for a user';

-- =============================================================================
-- Function 6: Delete old sessions and related data
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.delete_old_sessions(
    p_user_id INTEGER,
    p_older_than_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    deleted_sessions INTEGER,
    deleted_issues INTEGER,
    deleted_attachments INTEGER
) AS $$
DECLARE
    v_sessions_deleted INTEGER;
    v_issues_deleted INTEGER;
    v_attachments_deleted INTEGER;
    cutoff_date TIMESTAMPTZ;
BEGIN
    cutoff_date := CURRENT_TIMESTAMP - (p_older_than_days || ' days')::INTERVAL;

    -- Count before deletion
    SELECT COUNT(*) INTO v_sessions_deleted
    FROM ims.crawl_sessions
    WHERE user_id = p_user_id AND started_at < cutoff_date;

    SELECT COUNT(DISTINCT si.issue_pk) INTO v_issues_deleted
    FROM ims.session_issues si
    JOIN ims.crawl_sessions cs ON si.session_id = cs.session_id
    WHERE cs.user_id = p_user_id AND cs.started_at < cutoff_date;

    SELECT COUNT(*) INTO v_attachments_deleted
    FROM ims.attachments a
    JOIN ims.crawl_sessions cs ON a.session_id = cs.session_id
    WHERE cs.user_id = p_user_id AND cs.started_at < cutoff_date;

    -- Delete (cascade will handle related records)
    DELETE FROM ims.crawl_sessions
    WHERE user_id = p_user_id AND started_at < cutoff_date;

    -- Return results
    RETURN QUERY SELECT v_sessions_deleted, v_issues_deleted, v_attachments_deleted;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ims.delete_old_sessions IS 'Delete sessions older than specified days';

-- =============================================================================
-- Function 7: Search issues with full-text search
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.search_issues(
    p_search_query TEXT,
    p_product VARCHAR(100) DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    issue_pk BIGINT,
    issue_id VARCHAR(50),
    title TEXT,
    description TEXT,
    product VARCHAR(100),
    status VARCHAR(50),
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.issue_pk,
        i.issue_id,
        i.title,
        i.description,
        i.product,
        i.status,
        ts_rank(
            to_tsvector('english', COALESCE(i.title, '') || ' ' || COALESCE(i.description, '')),
            plainto_tsquery('english', p_search_query)
        ) AS rank
    FROM ims.issues i
    WHERE
        to_tsvector('english', COALESCE(i.title, '') || ' ' || COALESCE(i.description, ''))
        @@ plainto_tsquery('english', p_search_query)
        AND (p_product IS NULL OR i.product = p_product)
    ORDER BY rank DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ims.search_issues IS 'Full-text search across issue titles and descriptions';

-- =============================================================================
-- Success message
-- =============================================================================

DO $$
DECLARE
    function_count INTEGER;
    trigger_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO function_count
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'ims';

    SELECT COUNT(*) INTO trigger_count
    FROM pg_trigger t
    JOIN pg_class c ON t.tgrelid = c.oid
    JOIN pg_namespace n ON c.relnamespace = n.oid
    WHERE n.nspname = 'ims';

    RAISE NOTICE '✅ Functions and triggers created successfully!';
    RAISE NOTICE 'Functions: %, Triggers: %', function_count, trigger_count;
    RAISE NOTICE 'Next step: Run 05_create_views.sql';
END $$;
