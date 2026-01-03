## SQLAlchemy ORM Models - Usage Guide

Complete guide for using the IMS Crawler database ORM models with SQLAlchemy 2.0.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Model Overview](#model-overview)
3. [Basic Operations (CRUD)](#basic-operations-crud)
4. [Relationships](#relationships)
5. [Querying](#querying)
6. [Advanced Patterns](#advanced-patterns)
7. [Row Level Security](#row-level-security)
8. [Best Practices](#best-practices)

## Quick Start

### Simple Query Example

```python
from database import get_session, User, CrawlSession

# Get a database session
with get_session() as session:
    # Query all users
    users = session.query(User).all()
    for user in users:
        print(f"{user.username}: {user.email}")

    # Query with filter
    admin = session.query(User).filter_by(role='admin').first()
    print(f"Admin: {admin.username}")

    # Query with relationship
    sessions = session.query(CrawlSession).filter_by(user_id=admin.user_id).all()
    print(f"Admin has {len(sessions)} sessions")
```

### Create New Record

```python
from database import get_session, User
from datetime import datetime

with get_session() as session:
    # Create new user
    new_user = User(
        username='john.doe',
        email='john.doe@company.com',
        full_name='John Doe',
        department='Engineering',
        role='user',
        is_active=True,
        preferences={'theme': 'dark'}
    )

    # Add to session and commit
    session.add(new_user)
    session.commit()

    print(f"Created user: {new_user.user_id}")
```

## Model Overview

### 12 ORM Models

1. **User** - User accounts and preferences
2. **CrawlSession** - Crawling session records
3. **Issue** - IMS issue information
4. **SessionIssue** - Session-issue association (many-to-many)
5. **IssueComment** - Issue comments
6. **IssueHistory** - Change history
7. **Attachment** - File attachments
8. **SearchQuery** - Search query history
9. **SessionError** - Error logging
10. **AnalyticsDaily** - Daily statistics
11. **AnalyticsMonthly** - Monthly trends
12. **AuditLog** - Audit trail

### Model Relationships

```
User (1) ←→ (N) CrawlSession
User (1) ←→ (N) SearchQuery
User (1) ←→ (N) AnalyticsDaily
User (1) ←→ (N) AnalyticsMonthly
User (1) ←→ (N) AuditLog

CrawlSession (1) ←→ (N) SessionIssue
CrawlSession (1) ←→ (N) SearchQuery
CrawlSession (1) ←→ (N) SessionError
CrawlSession (1) ←→ (N) Attachment

Issue (1) ←→ (N) SessionIssue
Issue (1) ←→ (N) IssueComment
Issue (1) ←→ (N) IssueHistory
Issue (1) ←→ (N) Attachment
```

## Basic Operations (CRUD)

### Create

```python
from database import get_session, CrawlSession
from datetime import datetime
import uuid

with get_session(user_id=2) as session:
    # Create new crawl session
    new_session = CrawlSession(
        session_uuid=str(uuid.uuid4()),
        user_id=2,
        product='OpenFrame',
        original_query='connection timeout',
        parsed_query='+connection +timeout',
        query_language='en',
        max_results=100,
        status='running',
        started_at=datetime.utcnow()
    )

    session.add(new_session)
    session.commit()

    # Access the generated ID
    print(f"Created session ID: {new_session.session_id}")
```

### Read

```python
from database import get_session, Issue

with get_session() as session:
    # Get by primary key
    issue = session.get(Issue, 1)  # SQLAlchemy 2.0 style
    print(f"Issue: {issue.issue_id}")

    # Query with filter
    issues = session.query(Issue).filter(
        Issue.product == 'OpenFrame',
        Issue.status == 'Open'
    ).all()

    # Query with multiple conditions
    high_priority = session.query(Issue).filter(
        Issue.priority == 'High',
        Issue.severity == 'Critical'
    ).all()
```

### Update

```python
from database import get_session, User

with get_session() as session:
    # Update single record
    user = session.query(User).filter_by(username='yijae.shin').first()
    user.department = 'R&D'
    user.preferences = {'theme': 'dark', 'language': 'ko'}
    session.commit()

    # Bulk update
    session.query(Issue).filter(
        Issue.status == 'New'
    ).update({
        Issue.status: 'Open'
    })
    session.commit()
```

### Delete

```python
from database import get_session, SearchQuery

with get_session(user_id=2) as session:
    # Delete single record
    query = session.query(SearchQuery).filter_by(query_id=10).first()
    if query:
        session.delete(query)
        session.commit()

    # Bulk delete
    session.query(SessionError).filter(
        SessionError.severity == 'info'
    ).delete()
    session.commit()
```

## Relationships

### One-to-Many

```python
from database import get_session, User

with get_session() as session:
    # Access user's sessions through relationship
    user = session.query(User).filter_by(username='yijae.shin').first()

    print(f"User: {user.username}")
    print(f"Total sessions: {len(user.crawl_sessions)}")

    for sess in user.crawl_sessions:
        print(f"  - {sess.session_uuid}: {sess.product} ({sess.status})")

    # Access user from session
    session_obj = user.crawl_sessions[0]
    print(f"Session belongs to: {session_obj.user.username}")
```

### Many-to-Many (through Association)

```python
from database import get_session, CrawlSession, Issue

with get_session() as session:
    # Get session with its issues
    crawl_session = session.query(CrawlSession).first()

    print(f"Session: {crawl_session.session_uuid}")
    print(f"Issues in this session:")

    for session_issue in crawl_session.session_issues:
        issue = session_issue.issue
        print(f"  - {issue.issue_id}: {issue.title}")
        print(f"    Crawl order: {session_issue.crawl_order}")
        print(f"    Duration: {session_issue.crawl_duration_ms}ms")

    # Get issue with its sessions
    issue = session.query(Issue).first()
    print(f"\nIssue {issue.issue_id} was crawled in sessions:")
    for session_issue in issue.session_issues:
        sess = session_issue.session
        print(f"  - {sess.session_uuid} ({sess.started_at})")
```

### Nested Relationships

```python
from database import get_session, Issue

with get_session() as session:
    issue = session.query(Issue).filter_by(issue_id='SAMPLE-001').first()

    # Access all related data
    print(f"Issue: {issue.issue_id}")
    print(f"Title: {issue.title}")

    print(f"\nComments ({len(issue.comments)}):")
    for comment in issue.comments:
        print(f"  - {comment.author}: {comment.content[:50]}...")

    print(f"\nHistory ({len(issue.history)}):")
    for h in issue.history:
        print(f"  - {h.changed_at}: {h.field_name} changed")

    print(f"\nAttachments ({len(issue.attachments)}):")
    for att in issue.attachments:
        print(f"  - {att.filename} ({att.file_type})")
```

## Querying

### Basic Filters

```python
from database import get_session, CrawlSession

with get_session() as session:
    # Equality
    sessions = session.query(CrawlSession).filter(
        CrawlSession.status == 'completed'
    ).all()

    # Inequality
    failed = session.query(CrawlSession).filter(
        CrawlSession.status != 'completed'
    ).all()

    # LIKE
    openframe = session.query(CrawlSession).filter(
        CrawlSession.product.like('Open%')
    ).all()

    # IN
    active_statuses = session.query(CrawlSession).filter(
        CrawlSession.status.in_(['running', 'completed'])
    ).all()

    # NULL check
    with_path = session.query(CrawlSession).filter(
        CrawlSession.data_path.isnot(None)
    ).all()
```

### Combining Filters

```python
from database import get_session, Issue
from sqlalchemy import and_, or_

with get_session() as session:
    # AND conditions
    critical = session.query(Issue).filter(
        and_(
            Issue.priority == 'High',
            Issue.severity == 'Critical',
            Issue.status == 'Open'
        )
    ).all()

    # OR conditions
    important = session.query(Issue).filter(
        or_(
            Issue.priority == 'High',
            Issue.severity == 'Critical'
        )
    ).all()

    # Mixed
    complex_filter = session.query(Issue).filter(
        and_(
            Issue.product == 'OpenFrame',
            or_(
                Issue.status == 'Open',
                Issue.status == 'In Progress'
            )
        )
    ).all()
```

### Ordering and Limiting

```python
from database import get_session, CrawlSession

with get_session() as session:
    # Order by
    recent = session.query(CrawlSession).order_by(
        CrawlSession.started_at.desc()
    ).all()

    # Multiple order by
    sorted_sessions = session.query(CrawlSession).order_by(
        CrawlSession.product,
        CrawlSession.started_at.desc()
    ).all()

    # Limit
    top_10 = session.query(CrawlSession).limit(10).all()

    # Offset and limit (pagination)
    page_2 = session.query(CrawlSession).offset(10).limit(10).all()
```

### Aggregation

```python
from database import get_session, Issue
from sqlalchemy import func

with get_session() as session:
    # Count
    total_issues = session.query(func.count(Issue.issue_pk)).scalar()
    print(f"Total issues: {total_issues}")

    # Count by group
    by_product = session.query(
        Issue.product,
        func.count(Issue.issue_pk)
    ).group_by(Issue.product).all()

    for product, count in by_product:
        print(f"{product}: {count} issues")

    # Average, min, max
    stats = session.query(
        func.avg(CrawlSession.duration_seconds),
        func.min(CrawlSession.duration_seconds),
        func.max(CrawlSession.duration_seconds)
    ).first()

    print(f"Avg: {stats[0]}, Min: {stats[1]}, Max: {stats[2]}")
```

### Joins

```python
from database import get_session, User, CrawlSession, Issue, SessionIssue

with get_session() as session:
    # Inner join
    results = session.query(User, CrawlSession).join(
        CrawlSession, User.user_id == CrawlSession.user_id
    ).all()

    for user, sess in results:
        print(f"{user.username}: {sess.session_uuid}")

    # Left outer join
    all_users = session.query(User, CrawlSession).outerjoin(
        CrawlSession, User.user_id == CrawlSession.user_id
    ).all()

    # Multiple joins
    session_issues_query = session.query(
        CrawlSession, Issue
    ).join(
        SessionIssue, CrawlSession.session_id == SessionIssue.session_id
    ).join(
        Issue, SessionIssue.issue_pk == Issue.issue_pk
    ).all()
```

### JSONB Queries

```python
from database import get_session, CrawlSession

with get_session() as session:
    # Query JSONB field
    with_nl_parsing = session.query(CrawlSession).filter(
        CrawlSession.session_metadata['nl_parsing']['method'].astext == 'rule_based'
    ).all()

    # Check if key exists
    with_version = session.query(CrawlSession).filter(
        CrawlSession.session_metadata.has_key('crawler_version')
    ).all()

    # Contains
    specific_config = session.query(CrawlSession).filter(
        CrawlSession.session_metadata.contains({'crawler_version': '1.0.0'})
    ).all()
```

## Advanced Patterns

### Bulk Operations

```python
from database import get_session, Issue

with get_session() as session:
    # Bulk insert
    issues = [
        Issue(
            issue_id=f'ISSUE-{i}',
            title=f'Issue {i}',
            product='OpenFrame',
            status='New'
        )
        for i in range(100, 200)
    ]

    session.bulk_save_objects(issues)
    session.commit()

    # Bulk update with mappings
    session.bulk_update_mappings(Issue, [
        {'issue_pk': 1, 'status': 'Closed'},
        {'issue_pk': 2, 'status': 'Closed'},
        {'issue_pk': 3, 'status': 'In Progress'},
    ])
    session.commit()
```

### Eager Loading

```python
from database import get_session, Issue
from sqlalchemy.orm import joinedload, selectinload

with get_session() as session:
    # Joined load (single query with JOIN)
    issues = session.query(Issue).options(
        joinedload(Issue.comments),
        joinedload(Issue.history)
    ).all()

    # No additional queries when accessing relationships
    for issue in issues:
        print(f"{issue.issue_id}: {len(issue.comments)} comments")

    # Select in load (two queries)
    issues = session.query(Issue).options(
        selectinload(Issue.attachments)
    ).all()
```

### Transactions

```python
from database import get_session, CrawlSession, Issue

with get_session() as session:
    try:
        # Start implicit transaction
        new_session = CrawlSession(...)
        session.add(new_session)

        new_issue = Issue(...)
        session.add(new_issue)

        # Commit both together
        session.commit()

    except Exception as e:
        # Automatic rollback on exception
        print(f"Transaction failed: {e}")
        raise
```

### Custom Queries with Raw SQL

```python
from database import get_session
from sqlalchemy import text

with get_session() as session:
    # Execute raw SQL
    result = session.execute(
        text("SELECT * FROM ims.issues WHERE product = :product"),
        {"product": "OpenFrame"}
    )

    for row in result:
        print(row)

    # Call stored function
    result = session.execute(
        text("SELECT * FROM ims.get_user_stats(:user_id)"),
        {"user_id": 2}
    )

    stats = result.first()
    print(f"Total sessions: {stats[0]}")
```

## Row Level Security

### Setting User Context

```python
from database import get_session
from sqlalchemy import text

# Set user context before queries
with get_session(user_id=2) as session:
    # This automatically sets RLS context
    # All queries will be filtered by user_id=2

    # Query will only return sessions for user 2
    from database import CrawlSession
    sessions = session.query(CrawlSession).all()

    print(f"User 2 has {len(sessions)} sessions")
```

### Manual RLS Context

```python
from database import get_session
from sqlalchemy import text

with get_session() as session:
    # Manually set user context
    session.execute(
        text("SELECT ims.set_current_user(:user_id)"),
        {"user_id": 2}
    )

    # Now all queries filtered for user 2
    from database import CrawlSession
    sessions = session.query(CrawlSession).all()
```

## Best Practices

### 1. Always Use Context Managers

```python
# Good
with get_session() as session:
    users = session.query(User).all()
    # Session automatically closed

# Bad
session = get_session()
users = session.query(User).all()
# Session not properly closed
```

### 2. Set User Context for RLS

```python
# Good - User context set
with get_session(user_id=2) as session:
    sessions = session.query(CrawlSession).all()

# Bad - No user context (RLS may block)
with get_session() as session:
    sessions = session.query(CrawlSession).all()
```

### 3. Use Relationships Instead of Manual Joins

```python
# Good - Using relationships
with get_session() as session:
    user = session.query(User).filter_by(username='john').first()
    for sess in user.crawl_sessions:
        print(sess.session_uuid)

# Bad - Manual joins
with get_session() as session:
    results = session.query(User, CrawlSession).join(
        CrawlSession, User.user_id == CrawlSession.user_id
    ).filter(User.username == 'john').all()
```

### 4. Eager Load When Accessing Multiple Relationships

```python
# Good - Eager loading
from sqlalchemy.orm import joinedload

with get_session() as session:
    issues = session.query(Issue).options(
        joinedload(Issue.comments),
        joinedload(Issue.history)
    ).all()

    for issue in issues:
        print(f"{issue.title}: {len(issue.comments)} comments")

# Bad - N+1 query problem
with get_session() as session:
    issues = session.query(Issue).all()
    for issue in issues:
        print(f"{issue.title}: {len(issue.comments)} comments")  # Each triggers a query!
```

### 5. Handle Exceptions Properly

```python
# Good
with get_session() as session:
    try:
        user = User(username='duplicate')
        session.add(user)
        session.commit()
    except IntegrityError as e:
        print(f"Duplicate username: {e}")
        # Transaction automatically rolled back

# Bad - No exception handling
with get_session() as session:
    user = User(username='duplicate')
    session.add(user)
    session.commit()  # May crash
```

### 6. Use Bulk Operations for Large Datasets

```python
# Good - Bulk insert
with get_session() as session:
    issues = [Issue(...) for i in range(1000)]
    session.bulk_save_objects(issues)
    session.commit()

# Bad - Individual inserts
with get_session() as session:
    for i in range(1000):
        session.add(Issue(...))
    session.commit()  # Very slow!
```

### 7. Close Long-Running Sessions

```python
# Good - Short-lived sessions
def process_batch(batch):
    with get_session() as session:
        # Process batch
        session.commit()

for batch in large_dataset:
    process_batch(batch)

# Bad - Long-running session
with get_session() as session:
    for batch in large_dataset:
        # Process batch
        session.commit()  # Connection held entire time
```

## Common Patterns

### Create Session with Issues

```python
from database import get_session, CrawlSession, Issue, SessionIssue
import uuid

with get_session(user_id=2) as session:
    # Create session
    crawl_session = CrawlSession(
        session_uuid=str(uuid.uuid4()),
        user_id=2,
        product='OpenFrame',
        original_query='error',
        parsed_query='+error',
        status='running'
    )
    session.add(crawl_session)
    session.flush()  # Get session_id without committing

    # Create issues and link to session
    for i in range(5):
        issue = Issue(
            issue_id=f'ISSUE-{i}',
            title=f'Issue {i}',
            product='OpenFrame'
        )
        session.add(issue)
        session.flush()

        # Create association
        session_issue = SessionIssue(
            session_id=crawl_session.session_id,
            issue_pk=issue.issue_pk,
            crawl_order=i + 1,
            crawl_duration_ms=1000
        )
        session.add(session_issue)

    session.commit()
```

### Update Session Status

```python
from database import get_session, CrawlSession
from datetime import datetime

with get_session(user_id=2) as session:
    sess = session.query(CrawlSession).filter_by(
        session_uuid='...'
    ).first()

    if sess:
        sess.status = 'completed'
        sess.completed_at = datetime.utcnow()
        sess.duration_seconds = int((sess.completed_at - sess.started_at).total_seconds())
        session.commit()
```

### Search Issues with Full-Text

```python
from database import get_session
from sqlalchemy import text

with get_session() as session:
    # Use database function
    result = session.execute(
        text("SELECT * FROM ims.search_issues(:query, :product, :limit)"),
        {"query": "connection timeout", "product": "OpenFrame", "limit": 50}
    )

    for row in result:
        print(f"{row.issue_id}: {row.title} (rank: {row.rank})")
```

## Testing

```python
# test_database.py
import pytest
from database import get_session, User, CrawlSession

def test_create_user():
    with get_session() as session:
        user = User(
            username='test_user',
            email='test@example.com',
            role='user'
        )
        session.add(user)
        session.commit()

        assert user.user_id is not None

        # Cleanup
        session.delete(user)
        session.commit()

def test_user_sessions_relationship():
    with get_session() as session:
        user = session.query(User).filter_by(username='yijae.shin').first()
        assert user is not None
        assert len(user.crawl_sessions) >= 0
```

## Reference

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- Database Schema: `database/schema_design.md`
- SQL Scripts: `database/sql/`
