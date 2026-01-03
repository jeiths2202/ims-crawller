#!/bin/bash

# =============================================================================
# IMS Crawler Database Setup Script
# =============================================================================
# Description: Execute all SQL scripts to set up the complete database
# Usage: ./setup_database.sh [options]
# Options:
#   --host HOST       PostgreSQL host (default: localhost)
#   --port PORT       PostgreSQL port (default: 5432)
#   --user USER       PostgreSQL user (default: postgres)
#   --skip-tablespace Skip tablespace creation (for Docker)
#   --dry-run         Show commands without executing
# =============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-postgres}"
SKIP_TABLESPACE=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            PG_HOST="$2"
            shift 2
            ;;
        --port)
            PG_PORT="$2"
            shift 2
            ;;
        --user)
            PG_USER="$2"
            shift 2
            ;;
        --skip-tablespace)
            SKIP_TABLESPACE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/sql"

# Check if SQL directory exists
if [ ! -d "$SQL_DIR" ]; then
    echo -e "${RED}Error: SQL directory not found: $SQL_DIR${NC}"
    exit 1
fi

# Function to print section header
print_header() {
    echo ""
    echo -e "${BLUE}=================================================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    echo ""
}

# Function to execute SQL file
execute_sql() {
    local sql_file=$1
    local description=$2

    echo -e "${YELLOW}➜${NC} Executing: $description"
    echo -e "  File: $(basename "$sql_file")"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}  [DRY RUN]${NC} Would execute: psql -h $PG_HOST -p $PG_PORT -U $PG_USER -f $sql_file"
        return 0
    fi

    if psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -f "$sql_file" 2>&1; then
        echo -e "${GREEN}✓${NC} Success: $description"
        return 0
    else
        echo -e "${RED}✗${NC} Failed: $description"
        return 1
    fi
}

# Main execution
print_header "IMS Crawler Database Setup"

echo "Configuration:"
echo "  Host: $PG_HOST"
echo "  Port: $PG_PORT"
echo "  User: $PG_USER"
echo "  Skip Tablespace: $SKIP_TABLESPACE"
echo "  Dry Run: $DRY_RUN"
echo ""

# Check PostgreSQL connection
if [ "$DRY_RUN" = false ]; then
    echo -e "${YELLOW}➜${NC} Testing PostgreSQL connection..."
    if ! psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -c "SELECT version();" > /dev/null 2>&1; then
        echo -e "${RED}✗${NC} Cannot connect to PostgreSQL server"
        echo "Please check your connection settings and ensure PostgreSQL is running."
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Connection successful"
fi

# Step 1: Create Tablespace (optional for Docker)
if [ "$SKIP_TABLESPACE" = false ]; then
    print_header "Step 1: Create Tablespace"
    execute_sql "$SQL_DIR/01_create_tablespace.sql" "Create dedicated tablespace"
else
    echo -e "${YELLOW}⚠${NC} Skipping tablespace creation (--skip-tablespace)"
fi

# Step 2: Create Database and Schema
print_header "Step 2: Create Database and Schema"
execute_sql "$SQL_DIR/02_create_database_schema.sql" "Create database, schema, and tables"

# Step 3: Create Indexes
print_header "Step 3: Create Indexes"
execute_sql "$SQL_DIR/03_create_indexes.sql" "Create performance indexes"

# Step 4: Create Functions and Triggers
print_header "Step 4: Create Functions and Triggers"
execute_sql "$SQL_DIR/04_create_functions.sql" "Create stored functions and triggers"

# Step 5: Create Views
print_header "Step 5: Create Views"
execute_sql "$SQL_DIR/05_create_views.sql" "Create views and materialized views"

# Step 6: Create Roles and Permissions
print_header "Step 6: Create Roles and Permissions"
execute_sql "$SQL_DIR/06_create_roles.sql" "Create roles and set up RLS"

# Step 7: Insert Initial Data
print_header "Step 7: Insert Initial Data"
execute_sql "$SQL_DIR/07_initial_data.sql" "Insert seed data and samples"

# Summary
print_header "Setup Complete!"

if [ "$DRY_RUN" = false ]; then
    echo -e "${GREEN}✓${NC} All SQL scripts executed successfully!"
    echo ""
    echo "Database setup summary:"
    echo "  - Database: ims_crawler"
    echo "  - Schema: ims"
    echo "  - Tables: 12"
    echo "  - Views: 5 regular + 2 materialized"
    echo "  - Functions: 7"
    echo "  - Roles: 3 (ims_admin, ims_user, ims_readonly)"
    echo ""
    echo "Next steps:"
    echo "  1. Set up application connection in config/settings.py"
    echo "  2. Test database connection with Python"
    echo "  3. Run the IMS crawler with database integration"
    echo ""
    echo "Default users created:"
    echo "  - admin (admin role)"
    echo "  - yijae.shin (user role)"
    echo "  - analyst (readonly role)"
    echo ""
    echo "You can connect to the database with:"
    echo "  psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d ims_crawler"
else
    echo -e "${BLUE}[DRY RUN]${NC} No changes were made to the database"
    echo "Run without --dry-run to execute the scripts"
fi

echo ""
