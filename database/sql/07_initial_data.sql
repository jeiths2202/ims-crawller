-- =============================================================================
-- IMS Crawler Database Setup - Step 7: Initial Data
-- =============================================================================
-- Description: Insert seed data and sample records
-- =============================================================================

\c ims_crawler
SET search_path TO ims, public;

-- =============================================================================
-- Insert Admin User
-- =============================================================================

INSERT INTO ims.users (
    username,
    email,
    full_name,
    department,
    role,
    is_active,
    preferences
) VALUES (
    'admin',
    'admin@company.com',
    'System Administrator',
    'IT',
    'admin',
    TRUE,
    '{
        "crawler_config": {
            "default_max_results": 100,
            "default_language": "en",
            "enable_attachments": true,
            "enable_comments": true
        },
        "ui_preferences": {
            "theme": "light",
            "notifications_enabled": true
        }
    }'::JSONB
) ON CONFLICT (username) DO NOTHING;

-- =============================================================================
-- Insert Default User (for testing)
-- =============================================================================

INSERT INTO ims.users (
    username,
    email,
    full_name,
    department,
    role,
    is_active,
    preferences
) VALUES (
    'yijae.shin',
    'yijae.shin@company.com',
    'Yijae Shin',
    'Engineering',
    'user',
    TRUE,
    '{
        "crawler_config": {
            "default_max_results": 50,
            "default_language": "ko",
            "enable_attachments": true,
            "enable_comments": true,
            "preferred_products": ["OpenFrame", "Tibero", "JEUS"]
        },
        "ui_preferences": {
            "theme": "dark",
            "notifications_enabled": true,
            "language": "ko"
        }
    }'::JSONB
) ON CONFLICT (username) DO NOTHING;

-- =============================================================================
-- Insert Read-only User (for analytics)
-- =============================================================================

INSERT INTO ims.users (
    username,
    email,
    full_name,
    department,
    role,
    is_active,
    preferences
) VALUES (
    'analyst',
    'analyst@company.com',
    'Data Analyst',
    'Business Intelligence',
    'readonly',
    TRUE,
    '{
        "ui_preferences": {
            "theme": "light",
            "default_dashboard": "analytics"
        }
    }'::JSONB
) ON CONFLICT (username) DO NOTHING;

-- =============================================================================
-- Sample Crawl Session (for testing)
-- =============================================================================

DO $$
DECLARE
    v_user_id INTEGER;
    v_session_id BIGINT;
    v_issue_pk BIGINT;
BEGIN
    -- Get user ID
    SELECT user_id INTO v_user_id FROM ims.users WHERE username = 'yijae.shin';

    -- Insert sample session
    INSERT INTO ims.crawl_sessions (
        session_uuid,
        user_id,
        product,
        original_query,
        parsed_query,
        query_language,
        max_results,
        status,
        started_at,
        completed_at,
        duration_seconds,
        total_issues_found,
        issues_crawled,
        attachments_downloaded,
        search_time_ms,
        crawl_time_ms,
        avg_issue_time_ms,
        data_path,
        metadata
    ) VALUES (
        'sample-session-' || gen_random_uuid()::TEXT,
        v_user_id,
        'OpenFrame',
        'error crash timeout',
        '+error +crash +timeout',
        'en',
        10,
        'completed',
        CURRENT_TIMESTAMP - INTERVAL '1 hour',
        CURRENT_TIMESTAMP - INTERVAL '30 minutes',
        1800,
        5,
        5,
        2,
        1500,
        28500,
        5700,
        '/data/users/yijae.shin/sessions/sample-session',
        '{
            "nl_parsing": {
                "method": "rule_based",
                "confidence": 0.95
            },
            "crawler_version": "1.0.0",
            "python_version": "3.11"
        }'::JSONB
    ) RETURNING session_id INTO v_session_id;

    -- Insert sample issue
    INSERT INTO ims.issues (
        issue_id,
        title,
        description,
        product,
        status,
        priority,
        severity,
        issue_type,
        reporter,
        owner,
        registered_date,
        modified_date,
        project_code,
        project_name,
        full_data
    ) VALUES (
        'SAMPLE-001',
        'Application crash on startup with error timeout',
        'The application crashes immediately after startup when trying to connect to the database. Error message shows connection timeout.',
        'OpenFrame',
        'Open',
        'High',
        'Critical',
        'Bug',
        'john.doe',
        'jane.smith',
        CURRENT_TIMESTAMP - INTERVAL '7 days',
        CURRENT_TIMESTAMP - INTERVAL '2 days',
        'PRJ-2024',
        'Enterprise System Migration',
        '{
            "environment": "Production",
            "version": "7.0.5",
            "os": "Linux",
            "database": "Tibero"
        }'::JSONB
    ) RETURNING issue_pk INTO v_issue_pk;

    -- Link session and issue
    INSERT INTO ims.session_issues (
        session_id,
        issue_pk,
        crawl_order,
        crawl_duration_ms,
        had_errors
    ) VALUES (
        v_session_id,
        v_issue_pk,
        1,
        5700,
        FALSE
    );

    -- Insert sample comment
    INSERT INTO ims.issue_comments (
        issue_pk,
        comment_number,
        author,
        content,
        commented_at
    ) VALUES (
        v_issue_pk,
        1,
        'tech.support',
        'We are investigating this issue. It appears to be related to database connection pool settings.',
        CURRENT_TIMESTAMP - INTERVAL '5 days'
    );

    -- Insert sample history
    INSERT INTO ims.issue_history (
        issue_pk,
        changed_by,
        changed_at,
        change_type,
        field_name,
        old_value,
        new_value,
        description
    ) VALUES (
        v_issue_pk,
        'jane.smith',
        CURRENT_TIMESTAMP - INTERVAL '3 days',
        'status_change',
        'status',
        'New',
        'Open',
        'Status changed from New to Open after initial investigation'
    );

    -- Insert sample search query
    INSERT INTO ims.search_queries (
        user_id,
        session_id,
        original_query,
        parsed_query,
        query_language,
        product,
        results_count,
        parsing_method,
        parsing_confidence,
        synonym_expanded
    ) VALUES (
        v_user_id,
        v_session_id,
        'error crash timeout',
        '+error +crash +timeout',
        'en',
        'OpenFrame',
        5,
        'rule_based',
        0.95,
        TRUE
    );

    -- Insert audit log entry
    INSERT INTO ims.audit_log (
        user_id,
        action,
        resource_type,
        resource_id,
        new_value
    ) VALUES (
        v_user_id,
        'session_created',
        'session',
        'sample-session',
        jsonb_build_object(
            'product', 'OpenFrame',
            'query', 'error crash timeout'
        )
    );

    RAISE NOTICE '✅ Sample data inserted successfully!';
    RAISE NOTICE 'Session ID: %, Issue PK: %', v_session_id, v_issue_pk;
END $$;

-- =============================================================================
-- Initialize Analytics Tables (seed with zero data for current month)
-- =============================================================================

DO $$
DECLARE
    v_user_id INTEGER;
BEGIN
    FOR v_user_id IN SELECT user_id FROM ims.users WHERE is_active = TRUE LOOP
        -- Initialize daily analytics for today
        INSERT INTO ims.analytics_daily (
            user_id,
            stat_date,
            sessions_count,
            successful_sessions,
            failed_sessions,
            issues_crawled,
            unique_issues,
            attachments_downloaded,
            product_stats
        ) VALUES (
            v_user_id,
            CURRENT_DATE,
            0, 0, 0, 0, 0, 0,
            '{}'::JSONB
        ) ON CONFLICT (user_id, stat_date) DO NOTHING;

        -- Initialize monthly analytics for current month
        INSERT INTO ims.analytics_monthly (
            user_id,
            year,
            month,
            total_sessions,
            total_issues_crawled,
            unique_issues,
            product_distribution
        ) VALUES (
            v_user_id,
            EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER,
            EXTRACT(MONTH FROM CURRENT_DATE)::INTEGER,
            0, 0, 0,
            '{}'::JSONB
        ) ON CONFLICT (user_id, year, month) DO NOTHING;
    END LOOP;

    RAISE NOTICE '✅ Analytics tables initialized for all active users';
END $$;

-- =============================================================================
-- Refresh Materialized Views
-- =============================================================================

REFRESH MATERIALIZED VIEW ims.mv_daily_session_summary;
REFRESH MATERIALIZED VIEW ims.mv_issue_trends;

-- =============================================================================
-- Verify Initial Data
-- =============================================================================

DO $$
DECLARE
    user_count INTEGER;
    session_count INTEGER;
    issue_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM ims.users;
    SELECT COUNT(*) INTO session_count FROM ims.crawl_sessions;
    SELECT COUNT(*) INTO issue_count FROM ims.issues;

    RAISE NOTICE '✅ Initial data verification:';
    RAISE NOTICE 'Users: %', user_count;
    RAISE NOTICE 'Sessions: %', session_count;
    RAISE NOTICE 'Issues: %', issue_count;
    RAISE NOTICE '';
    RAISE NOTICE '🎉 Database setup complete!';
    RAISE NOTICE 'Next step: Configure application connection settings';
END $$;
