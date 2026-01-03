# IMS Crawler Database Setup

This directory contains PostgreSQL database schema and setup scripts for IMS Crawler metadata management.

## Overview

The database system provides:
- **Metadata Storage**: Comprehensive tracking of crawl sessions, issues, and analytics
- **User Isolation**: Row-level security for multi-user environments
- **Performance Optimization**: Strategic indexes including full-text search
- **Analytics**: Daily and monthly aggregated statistics
- **Audit Trail**: Complete tracking of all operations

## Architecture

### Database Structure
- **Database**: `ims_crawler`
- **Schema**: `ims`
- **Tablespace**: `ims_metadata_tbs` (optional)
- **Tables**: 12 core tables with normalization
- **Views**: 5 regular views + 2 materialized views
- **Functions**: 7 stored functions for automation
- **Roles**: 3 roles with RLS policies

### 12-Table Schema

1. **users** - User accounts and preferences
2. **crawl_sessions** - Crawling session records
3. **issues** - IMS issue information
4. **session_issues** - Session-issue mapping (many-to-many)
5. **issue_comments** - Issue comments
6. **issue_history** - Change history
7. **attachments** - File attachments with text extraction
8. **search_queries** - Search query history
9. **session_errors** - Error logging
10. **analytics_daily** - Daily statistics
11. **analytics_monthly** - Monthly trends
12. **audit_log** - Audit trail

## Quick Start

### Prerequisites

- PostgreSQL 16+ running (Docker or native)
- Database user with CREATEDB privileges
- psql command-line tool

### Setup on Docker PostgreSQL

```bash
# Navigate to database directory
cd database

# Run setup script (skip tablespace for Docker)
bash setup_database.sh --host localhost --port 5432 --user postgres --skip-tablespace

# Or set environment variables
export PG_HOST=localhost
export PG_PORT=5432
export PG_USER=postgres
bash setup_database.sh --skip-tablespace
```

### Dry Run (Test Without Executing)

```bash
bash setup_database.sh --skip-tablespace --dry-run
```

### Manual Execution

```bash
# Execute SQL scripts in order
psql -h localhost -p 5432 -U postgres -f sql/02_create_database_schema.sql
psql -h localhost -p 5432 -U postgres -f sql/03_create_indexes.sql
psql -h localhost -p 5432 -U postgres -f sql/04_create_functions.sql
psql -h localhost -p 5432 -U postgres -f sql/05_create_views.sql
psql -h localhost -p 5432 -U postgres -f sql/06_create_roles.sql
psql -h localhost -p 5432 -U postgres -f sql/07_initial_data.sql
```

## SQL Scripts

### 01_create_tablespace.sql
Creates dedicated tablespace for IMS metadata storage.

**Note**: Skip this for Docker installations where you don't have file system access.

### 02_create_database_schema.sql
Creates the `ims_crawler` database, `ims` schema, and all 12 tables.

Key features:
- Normalized table structure
- JSONB columns for flexible metadata
- Foreign key constraints
- Timestamps with timezone support

### 03_create_indexes.sql
Creates performance indexes:
- B-tree indexes on foreign keys
- GIN indexes for JSONB and full-text search
- Composite indexes for common queries
- Partial indexes for active records

### 04_create_functions.sql
Stored functions and triggers:
- `update_updated_at()` - Auto-update timestamps
- `aggregate_daily_stats()` - Daily statistics aggregation
- `aggregate_monthly_stats()` - Monthly analytics
- `upsert_issue()` - Insert or update issues
- `get_user_stats()` - User statistics retrieval
- `delete_old_sessions()` - Cleanup old data
- `search_issues()` - Full-text search

### 05_create_views.sql
Views for common queries:
- `v_user_dashboard` - User statistics overview
- `v_session_detail` - Detailed session information
- `v_issue_search` - Issue search with counts
- `v_recent_activity` - Recent user activity
- `v_product_stats` - Product-based statistics
- `mv_daily_session_summary` - Materialized daily summary
- `mv_issue_trends` - Materialized issue trends

### 06_create_roles.sql
Database roles and Row Level Security:
- `ims_admin` - Full administrative access
- `ims_user` - Read/write own data
- `ims_readonly` - Read-only access
- RLS policies for user data isolation

### 07_initial_data.sql
Seed data:
- Default admin user
- Sample user (yijae.shin)
- Read-only analyst user
- Sample crawl session
- Sample issue data
- Analytics initialization

## Database Roles

### ims_admin
- Full access to all tables and functions
- Can manage users and permissions
- No RLS restrictions

### ims_user
- Read/write access to own data
- RLS enforces data isolation
- Can execute user functions
- Cannot modify other users' data

### ims_readonly
- Read-only access to all data
- Can view analytics and reports
- Cannot modify any data

## Row Level Security (RLS)

RLS policies ensure users can only access their own data:

```sql
-- Set current user context (required before queries)
SELECT ims.set_current_user(123);  -- user_id

-- Now all queries automatically filter by user_id
SELECT * FROM ims.crawl_sessions;  -- Only returns user 123's sessions
```

## Python Integration

### Environment Variables

Add to `.env`:

```env
# PostgreSQL Connection
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=ims_crawler
DATABASE_USER=ims_user
DATABASE_PASSWORD=your_password_here
DATABASE_SCHEMA=ims

# Connection Pool Settings
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
```

### SQLAlchemy Connection

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Connection string
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    echo=False  # Set to True for SQL logging
)

# Create session factory
SessionLocal = sessionmaker(bind=engine)

# Use in context manager
with SessionLocal() as session:
    # Set current user for RLS
    session.execute("SELECT ims.set_current_user(:user_id)", {"user_id": 123})

    # Execute queries
    sessions = session.query(CrawlSession).all()
```

## Common Operations

### Aggregate Daily Statistics

```sql
-- Aggregate stats for yesterday (runs automatically via cron)
SELECT ims.aggregate_daily_stats();

-- Aggregate for specific date
SELECT ims.aggregate_daily_stats('2024-01-15');
```

### Delete Old Sessions

```sql
-- Delete sessions older than 90 days for user 123
SELECT * FROM ims.delete_old_sessions(123, 90);
```

### Full-Text Search

```sql
-- Search issues
SELECT * FROM ims.search_issues('connection timeout', 'OpenFrame', 50);
```

### Refresh Materialized Views

```sql
-- Refresh all materialized views
SELECT ims.refresh_materialized_views();

-- Or individually
REFRESH MATERIALIZED VIEW CONCURRENTLY ims.mv_daily_session_summary;
```

### User Statistics

```sql
-- Get comprehensive user stats
SELECT * FROM ims.get_user_stats(123);
```

## Maintenance

### Daily Tasks (Automate with cron)

```sql
-- 1. Aggregate daily statistics (run at 2 AM)
SELECT ims.aggregate_daily_stats(CURRENT_DATE - INTERVAL '1 day');

-- 2. Refresh materialized views (run at 3 AM)
SELECT ims.refresh_materialized_views();

-- 3. Cleanup old data (run weekly)
-- Delete sessions older than 90 days for all users
DO $$
DECLARE
    user_rec RECORD;
BEGIN
    FOR user_rec IN SELECT user_id FROM ims.users WHERE is_active = TRUE LOOP
        PERFORM ims.delete_old_sessions(user_rec.user_id, 90);
    END LOOP;
END $$;
```

### Monthly Tasks

```sql
-- Aggregate monthly statistics (run on 1st of month)
SELECT ims.aggregate_monthly_stats(
    EXTRACT(YEAR FROM CURRENT_DATE - INTERVAL '1 month')::INTEGER,
    EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 month')::INTEGER
);

-- Vacuum and analyze
VACUUM ANALYZE ims.crawl_sessions;
VACUUM ANALYZE ims.issues;
```

### Backup

```bash
# Full database backup
pg_dump -h localhost -p 5432 -U postgres -F c -b -v -f "ims_crawler_$(date +%Y%m%d).backup" ims_crawler

# Schema only
pg_dump -h localhost -p 5432 -U postgres -s -f "ims_crawler_schema.sql" ims_crawler

# Data only
pg_dump -h localhost -p 5432 -U postgres -a -f "ims_crawler_data.sql" ims_crawler
```

### Restore

```bash
# Restore from custom format backup
pg_restore -h localhost -p 5432 -U postgres -d ims_crawler -v "ims_crawler_20240115.backup"

# Restore from SQL dump
psql -h localhost -p 5432 -U postgres -d ims_crawler -f "ims_crawler_backup.sql"
```

## Monitoring

### Check Database Size

```sql
SELECT
    pg_size_pretty(pg_database_size('ims_crawler')) AS database_size,
    pg_size_pretty(pg_total_relation_size('ims.crawl_sessions')) AS sessions_size,
    pg_size_pretty(pg_total_relation_size('ims.issues')) AS issues_size;
```

### Active Connections

```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = 'ims_crawler';
```

### Table Statistics

```sql
SELECT
    schemaname,
    tablename,
    n_live_tup AS row_count,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size
FROM pg_stat_user_tables
WHERE schemaname = 'ims'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Index Usage

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'ims'
ORDER BY idx_scan DESC;
```

## Troubleshooting

### Connection Issues

```bash
# Test connection
psql -h localhost -p 5432 -U postgres -c "SELECT version();"

# Check if database exists
psql -h localhost -p 5432 -U postgres -l | grep ims_crawler

# Check if schema exists
psql -h localhost -p 5432 -U postgres -d ims_crawler -c "\dn"
```

### Permission Issues

```sql
-- Check current user permissions
SELECT * FROM information_schema.role_table_grants WHERE grantee = 'ims_user';

-- Check RLS policies
SELECT * FROM pg_policies WHERE schemaname = 'ims';
```

### Performance Issues

```sql
-- Find slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Analyze table
ANALYZE ims.crawl_sessions;

-- Check for missing indexes
SELECT * FROM pg_stat_user_tables WHERE schemaname = 'ims' AND seq_scan > 1000;
```

## Reference

### Complete Schema Diagram

See `schema_design.md` for detailed ERD and table relationships.

### Table Relationships

```
users (1) ←→ (N) crawl_sessions
crawl_sessions (1) ←→ (N) session_issues
issues (1) ←→ (N) session_issues
issues (1) ←→ (N) issue_comments
issues (1) ←→ (N) issue_history
issues (1) ←→ (N) attachments
crawl_sessions (1) ←→ (N) attachments
users (1) ←→ (N) search_queries
crawl_sessions (1) ←→ (N) search_queries
crawl_sessions (1) ←→ (N) session_errors
```

### Key Constraints

- All tables have primary keys (BIGSERIAL or SERIAL)
- Foreign keys with CASCADE DELETE on sessions
- UNIQUE constraints on business keys (username, issue_id, session_uuid)
- CHECK constraints on enum-like fields (status, role, severity)

## Support

For issues or questions:
1. Check this README
2. Review `schema_design.md` for detailed documentation
3. Examine SQL scripts in `sql/` directory
4. Check PostgreSQL logs for error messages
