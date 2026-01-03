-- =============================================================================
-- IMS Crawler Database Setup - Step 6: Roles and Permissions
-- =============================================================================
-- Description: Create database roles and set up Row Level Security (RLS)
-- =============================================================================

\c ims_crawler
SET search_path TO ims, public;

-- =============================================================================
-- Role 1: ims_admin - Full administrative access
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ims_admin') THEN
        CREATE ROLE ims_admin WITH
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT
            NOREPLICATION
            CONNECTION LIMIT -1;
    END IF;
END $$;

-- Grant all privileges on schema
GRANT USAGE ON SCHEMA ims TO ims_admin;
GRANT ALL PRIVILEGES ON SCHEMA ims TO ims_admin;

-- Grant all privileges on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ims TO ims_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ims TO ims_admin;

-- Grant execute on all functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ims TO ims_admin;

-- Grant for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA ims
    GRANT ALL PRIVILEGES ON TABLES TO ims_admin;

ALTER DEFAULT PRIVILEGES IN SCHEMA ims
    GRANT ALL PRIVILEGES ON SEQUENCES TO ims_admin;

ALTER DEFAULT PRIVILEGES IN SCHEMA ims
    GRANT EXECUTE ON FUNCTIONS TO ims_admin;

COMMENT ON ROLE ims_admin IS 'Administrator role with full access to IMS schema';

-- =============================================================================
-- Role 2: ims_user - Regular user with read/write access to own data
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ims_user') THEN
        CREATE ROLE ims_user WITH
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT
            NOREPLICATION
            CONNECTION LIMIT -1;
    END IF;
END $$;

-- Grant schema usage
GRANT USAGE ON SCHEMA ims TO ims_user;

-- Grant select on reference tables
GRANT SELECT ON ims.users TO ims_user;

-- Grant read/write on user data tables
GRANT SELECT, INSERT, UPDATE ON ims.crawl_sessions TO ims_user;
GRANT SELECT, INSERT, UPDATE ON ims.issues TO ims_user;
GRANT SELECT, INSERT, UPDATE ON ims.session_issues TO ims_user;
GRANT SELECT, INSERT, UPDATE ON ims.issue_comments TO ims_user;
GRANT SELECT, INSERT, UPDATE ON ims.issue_history TO ims_user;
GRANT SELECT, INSERT, UPDATE ON ims.attachments TO ims_user;
GRANT SELECT, INSERT ON ims.search_queries TO ims_user;
GRANT SELECT, INSERT ON ims.session_errors TO ims_user;
GRANT SELECT, INSERT ON ims.audit_log TO ims_user;

-- Grant select on analytics tables
GRANT SELECT ON ims.analytics_daily TO ims_user;
GRANT SELECT ON ims.analytics_monthly TO ims_user;

-- Grant select on views
GRANT SELECT ON ims.v_user_dashboard TO ims_user;
GRANT SELECT ON ims.v_session_detail TO ims_user;
GRANT SELECT ON ims.v_issue_search TO ims_user;
GRANT SELECT ON ims.v_recent_activity TO ims_user;
GRANT SELECT ON ims.v_product_stats TO ims_user;
GRANT SELECT ON ims.mv_daily_session_summary TO ims_user;
GRANT SELECT ON ims.mv_issue_trends TO ims_user;

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ims TO ims_user;

-- Grant execute on specific functions
GRANT EXECUTE ON FUNCTION ims.upsert_issue TO ims_user;
GRANT EXECUTE ON FUNCTION ims.get_user_stats TO ims_user;
GRANT EXECUTE ON FUNCTION ims.search_issues TO ims_user;
GRANT EXECUTE ON FUNCTION ims.delete_old_sessions TO ims_user;

COMMENT ON ROLE ims_user IS 'Regular user role with read/write access to own data';

-- =============================================================================
-- Role 3: ims_readonly - Read-only access for analysis and reporting
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ims_readonly') THEN
        CREATE ROLE ims_readonly WITH
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT
            NOREPLICATION
            CONNECTION LIMIT -1;
    END IF;
END $$;

-- Grant schema usage
GRANT USAGE ON SCHEMA ims TO ims_readonly;

-- Grant select on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA ims TO ims_readonly;

-- Grant select on all views
GRANT SELECT ON ims.v_user_dashboard TO ims_readonly;
GRANT SELECT ON ims.v_session_detail TO ims_readonly;
GRANT SELECT ON ims.v_issue_search TO ims_readonly;
GRANT SELECT ON ims.v_recent_activity TO ims_readonly;
GRANT SELECT ON ims.v_product_stats TO ims_readonly;
GRANT SELECT ON ims.mv_daily_session_summary TO ims_readonly;
GRANT SELECT ON ims.mv_issue_trends TO ims_readonly;

-- Grant execute on read-only functions
GRANT EXECUTE ON FUNCTION ims.get_user_stats TO ims_readonly;
GRANT EXECUTE ON FUNCTION ims.search_issues TO ims_readonly;

COMMENT ON ROLE ims_readonly IS 'Read-only role for analysis and reporting';

-- =============================================================================
-- Row Level Security (RLS) - User data isolation
-- =============================================================================

-- Enable RLS on crawl_sessions
ALTER TABLE ims.crawl_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY crawl_sessions_user_isolation ON ims.crawl_sessions
    FOR ALL
    TO ims_user
    USING (user_id = current_setting('app.current_user_id')::INTEGER)
    WITH CHECK (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY crawl_sessions_admin_access ON ims.crawl_sessions
    FOR ALL
    TO ims_admin
    USING (true)
    WITH CHECK (true);

CREATE POLICY crawl_sessions_readonly_access ON ims.crawl_sessions
    FOR SELECT
    TO ims_readonly
    USING (true);

COMMENT ON POLICY crawl_sessions_user_isolation ON ims.crawl_sessions IS 'Users can only access their own sessions';

-- Enable RLS on search_queries
ALTER TABLE ims.search_queries ENABLE ROW LEVEL SECURITY;

CREATE POLICY search_queries_user_isolation ON ims.search_queries
    FOR ALL
    TO ims_user
    USING (user_id = current_setting('app.current_user_id')::INTEGER)
    WITH CHECK (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY search_queries_admin_access ON ims.search_queries
    FOR ALL
    TO ims_admin
    USING (true)
    WITH CHECK (true);

CREATE POLICY search_queries_readonly_access ON ims.search_queries
    FOR SELECT
    TO ims_readonly
    USING (true);

-- Enable RLS on analytics_daily
ALTER TABLE ims.analytics_daily ENABLE ROW LEVEL SECURITY;

CREATE POLICY analytics_daily_user_isolation ON ims.analytics_daily
    FOR SELECT
    TO ims_user
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY analytics_daily_admin_access ON ims.analytics_daily
    FOR ALL
    TO ims_admin
    USING (true)
    WITH CHECK (true);

CREATE POLICY analytics_daily_readonly_access ON ims.analytics_daily
    FOR SELECT
    TO ims_readonly
    USING (true);

-- Enable RLS on analytics_monthly
ALTER TABLE ims.analytics_monthly ENABLE ROW LEVEL SECURITY;

CREATE POLICY analytics_monthly_user_isolation ON ims.analytics_monthly
    FOR SELECT
    TO ims_user
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY analytics_monthly_admin_access ON ims.analytics_monthly
    FOR ALL
    TO ims_admin
    USING (true)
    WITH CHECK (true);

CREATE POLICY analytics_monthly_readonly_access ON ims.analytics_monthly
    FOR SELECT
    TO ims_readonly
    USING (true);

-- Enable RLS on audit_log
ALTER TABLE ims.audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_log_user_view ON ims.audit_log
    FOR SELECT
    TO ims_user
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY audit_log_admin_access ON ims.audit_log
    FOR ALL
    TO ims_admin
    USING (true)
    WITH CHECK (true);

CREATE POLICY audit_log_readonly_access ON ims.audit_log
    FOR SELECT
    TO ims_readonly
    USING (true);

-- =============================================================================
-- Helper Function: Set current user context
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.set_current_user(p_user_id INTEGER)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_user_id', p_user_id::TEXT, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION ims.set_current_user(INTEGER) IS 'Set current user context for RLS policies';

-- Grant execute to all roles
GRANT EXECUTE ON FUNCTION ims.set_current_user TO ims_admin, ims_user, ims_readonly;

-- =============================================================================
-- Helper Function: Get current user ID
-- =============================================================================

CREATE OR REPLACE FUNCTION ims.get_current_user_id()
RETURNS INTEGER AS $$
BEGIN
    RETURN current_setting('app.current_user_id', true)::INTEGER;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION ims.get_current_user_id() IS 'Get current user ID from session context';

-- Grant execute to all roles
GRANT EXECUTE ON FUNCTION ims.get_current_user_id TO ims_admin, ims_user, ims_readonly;

-- =============================================================================
-- Success message
-- =============================================================================

DO $$
DECLARE
    role_count INTEGER;
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO role_count
    FROM pg_roles
    WHERE rolname IN ('ims_admin', 'ims_user', 'ims_readonly');

    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'ims';

    RAISE NOTICE '✅ Roles and permissions created successfully!';
    RAISE NOTICE 'Roles: %, RLS policies: %', role_count, policy_count;
    RAISE NOTICE 'Next step: Run 07_initial_data.sql';
END $$;
