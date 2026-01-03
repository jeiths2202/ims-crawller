-- =============================================================================
-- IMS Crawler Database Setup - Step 1: Tablespace
-- =============================================================================
-- Description: Create dedicated tablespace for IMS Crawler metadata
-- Note: Adjust path according to your system
-- =============================================================================

-- Create tablespace directory (execute outside PostgreSQL)
-- mkdir -p /var/lib/postgresql/data/ims_metadata
-- chown postgres:postgres /var/lib/postgresql/data/ims_metadata

-- Create tablespace
-- Note: In Docker, use container's data directory
CREATE TABLESPACE ims_metadata_tbs
    LOCATION '/var/lib/postgresql/data/ims_metadata';

COMMENT ON TABLESPACE ims_metadata_tbs IS 'Tablespace for IMS Crawler metadata';

-- Verify tablespace creation
SELECT spcname, pg_tablespace_location(oid) AS location
FROM pg_tablespace
WHERE spcname = 'ims_metadata_tbs';
