-- =============================================================================
-- IMS Crawler Database Setup - Step 3: Indexes
-- =============================================================================
-- Description: Create indexes for performance optimization
-- =============================================================================

\c ims_crawler
SET search_path TO ims, public;

-- =============================================================================
-- Indexes for users table
-- =============================================================================

CREATE INDEX idx_users_username ON ims.users(username);
CREATE INDEX idx_users_is_active ON ims.users(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_users_role ON ims.users(role);

-- =============================================================================
-- Indexes for crawl_sessions table
-- =============================================================================

CREATE INDEX idx_sessions_user_id ON ims.crawl_sessions(user_id);
CREATE INDEX idx_sessions_product ON ims.crawl_sessions(product);
CREATE INDEX idx_sessions_status ON ims.crawl_sessions(status);
CREATE INDEX idx_sessions_started_at ON ims.crawl_sessions(started_at DESC);
CREATE INDEX idx_sessions_uuid ON ims.crawl_sessions(session_uuid);
CREATE INDEX idx_sessions_user_product ON ims.crawl_sessions(user_id, product);
CREATE INDEX idx_sessions_user_date ON ims.crawl_sessions(user_id, DATE(started_at));

-- JSONB index for metadata
CREATE INDEX idx_sessions_metadata ON ims.crawl_sessions USING GIN(metadata);

-- =============================================================================
-- Indexes for issues table
-- =============================================================================

CREATE INDEX idx_issues_issue_id ON ims.issues(issue_id);
CREATE INDEX idx_issues_product ON ims.issues(product);
CREATE INDEX idx_issues_status ON ims.issues(status);
CREATE INDEX idx_issues_priority ON ims.issues(priority);
CREATE INDEX idx_issues_registered_date ON ims.issues(registered_date DESC);
CREATE INDEX idx_issues_modified_date ON ims.issues(modified_date DESC);
CREATE INDEX idx_issues_product_status ON ims.issues(product, status);

-- Full-text search indexes
CREATE INDEX idx_issues_title_fts ON ims.issues
    USING GIN(to_tsvector('english', COALESCE(title, '')));

CREATE INDEX idx_issues_description_fts ON ims.issues
    USING GIN(to_tsvector('english', COALESCE(description, '')));

-- JSONB index for full_data
CREATE INDEX idx_issues_full_data ON ims.issues USING GIN(full_data);

-- =============================================================================
-- Indexes for session_issues table
-- =============================================================================

CREATE INDEX idx_session_issues_session_id ON ims.session_issues(session_id);
CREATE INDEX idx_session_issues_issue_pk ON ims.session_issues(issue_pk);
CREATE INDEX idx_session_issues_crawl_order ON ims.session_issues(session_id, crawl_order);

-- =============================================================================
-- Indexes for issue_comments table
-- =============================================================================

CREATE INDEX idx_comments_issue_pk ON ims.issue_comments(issue_pk);
CREATE INDEX idx_comments_author ON ims.issue_comments(author);
CREATE INDEX idx_comments_commented_at ON ims.issue_comments(commented_at DESC);

-- Full-text search on comments
CREATE INDEX idx_comments_content_fts ON ims.issue_comments
    USING GIN(to_tsvector('english', COALESCE(content, '')));

-- =============================================================================
-- Indexes for issue_history table
-- =============================================================================

CREATE INDEX idx_history_issue_pk ON ims.issue_history(issue_pk);
CREATE INDEX idx_history_changed_at ON ims.issue_history(changed_at DESC);
CREATE INDEX idx_history_change_type ON ims.issue_history(change_type);
CREATE INDEX idx_history_changed_by ON ims.issue_history(changed_by);

-- =============================================================================
-- Indexes for attachments table
-- =============================================================================

CREATE INDEX idx_attachments_issue_pk ON ims.attachments(issue_pk);
CREATE INDEX idx_attachments_session_id ON ims.attachments(session_id);
CREATE INDEX idx_attachments_file_type ON ims.attachments(file_type);
CREATE INDEX idx_attachments_downloaded ON ims.attachments(downloaded);

-- Full-text search on extracted text
CREATE INDEX idx_attachments_text_fts ON ims.attachments
    USING GIN(to_tsvector('english', COALESCE(extracted_text, '')));

-- =============================================================================
-- Indexes for search_queries table
-- =============================================================================

CREATE INDEX idx_queries_user_id ON ims.search_queries(user_id);
CREATE INDEX idx_queries_session_id ON ims.search_queries(session_id);
CREATE INDEX idx_queries_product ON ims.search_queries(product);
CREATE INDEX idx_queries_queried_at ON ims.search_queries(queried_at DESC);
CREATE INDEX idx_queries_user_date ON ims.search_queries(user_id, DATE(queried_at));

-- Full-text search on queries
CREATE INDEX idx_queries_original_fts ON ims.search_queries
    USING GIN(to_tsvector('english', COALESCE(original_query, '')));

-- =============================================================================
-- Indexes for session_errors table
-- =============================================================================

CREATE INDEX idx_errors_session_id ON ims.session_errors(session_id);
CREATE INDEX idx_errors_error_type ON ims.session_errors(error_type);
CREATE INDEX idx_errors_severity ON ims.session_errors(severity);
CREATE INDEX idx_errors_occurred_at ON ims.session_errors(occurred_at DESC);

-- JSONB index for error_detail
CREATE INDEX idx_errors_detail ON ims.session_errors USING GIN(error_detail);

-- =============================================================================
-- Indexes for analytics_daily table
-- =============================================================================

CREATE INDEX idx_analytics_daily_user_id ON ims.analytics_daily(user_id);
CREATE INDEX idx_analytics_daily_stat_date ON ims.analytics_daily(stat_date DESC);
CREATE INDEX idx_analytics_daily_user_date ON ims.analytics_daily(user_id, stat_date DESC);

-- =============================================================================
-- Indexes for analytics_monthly table
-- =============================================================================

CREATE INDEX idx_analytics_monthly_user_id ON ims.analytics_monthly(user_id);
CREATE INDEX idx_analytics_monthly_year_month ON ims.analytics_monthly(year DESC, month DESC);
CREATE INDEX idx_analytics_monthly_user_year_month ON ims.analytics_monthly(user_id, year DESC, month DESC);

-- =============================================================================
-- Indexes for audit_log table
-- =============================================================================

CREATE INDEX idx_audit_user_id ON ims.audit_log(user_id);
CREATE INDEX idx_audit_action ON ims.audit_log(action);
CREATE INDEX idx_audit_resource_type ON ims.audit_log(resource_type);
CREATE INDEX idx_audit_created_at ON ims.audit_log(created_at DESC);
CREATE INDEX idx_audit_resource ON ims.audit_log(resource_type, resource_id);

-- =============================================================================
-- Analyze tables for optimizer statistics
-- =============================================================================

ANALYZE ims.users;
ANALYZE ims.crawl_sessions;
ANALYZE ims.issues;
ANALYZE ims.session_issues;
ANALYZE ims.issue_comments;
ANALYZE ims.issue_history;
ANALYZE ims.attachments;
ANALYZE ims.search_queries;
ANALYZE ims.session_errors;
ANALYZE ims.analytics_daily;
ANALYZE ims.analytics_monthly;
ANALYZE ims.audit_log;

-- =============================================================================
-- Success message
-- =============================================================================

DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'ims';

    RAISE NOTICE '✅ Indexes created successfully!';
    RAISE NOTICE 'Total indexes in ims schema: %', index_count;
    RAISE NOTICE 'Next step: Run 04_create_functions.sql';
END $$;
