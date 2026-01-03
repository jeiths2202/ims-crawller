# SQLAlchemy ORM - Quick Reference Card

Quick reference for common database operations with IMS Crawler ORM models.

## Import Models

```python
from database import (
    get_session,
    User, CrawlSession, Issue, SessionIssue,
    IssueComment, IssueHistory, Attachment,
    SearchQuery, SessionError, AnalyticsDaily
)
```

## Basic Operations

### Create

```python
# Single record
with get_session(user_id=2) as session:
    user = User(username='john', email='john@example.com')
    session.add(user)
    session.commit()
    print(user.user_id)  # Auto-generated ID

# Multiple records
with get_session() as session:
    issues = [Issue(issue_id=f'I-{i}', title=f'Issue {i}') for i in range(10)]
    session.add_all(issues)
    session.commit()
```

### Read

```python
with get_session() as session:
    # Get by primary key
    user = session.get(User, 1)

    # Get first match
    admin = session.query(User).filter_by(role='admin').first()

    # Get all
    users = session.query(User).all()

    # Count
    count = session.query(User).count()
```

### Update

```python
with get_session() as session:
    user = session.query(User).filter_by(username='john').first()
    user.email = 'newemail@example.com'
    session.commit()
```

### Delete

```python
with get_session() as session:
    user = session.query(User).filter_by(username='john').first()
    session.delete(user)
    session.commit()
```

## Filtering

```python
with get_session() as session:
    # Equality
    User.query(User).filter(User.role == 'admin')

    # Not equal
    User.query(User).filter(User.role != 'admin')

    # Multiple conditions (AND)
    session.query(Issue).filter(
        Issue.product == 'OpenFrame',
        Issue.status == 'Open'
    )

    # OR conditions
    from sqlalchemy import or_
    session.query(Issue).filter(
        or_(Issue.priority == 'High', Issue.severity == 'Critical')
    )

    # IN
    session.query(User).filter(User.role.in_(['admin', 'user']))

    # LIKE
    session.query(Issue).filter(Issue.title.like('%error%'))

    # NULL check
    session.query(Issue).filter(Issue.closed_date.is_(None))
    session.query(Issue).filter(Issue.closed_date.isnot(None))
```

## Ordering & Limiting

```python
with get_session() as session:
    # Order by
    session.query(CrawlSession).order_by(CrawlSession.started_at.desc())

    # Multiple order
    session.query(Issue).order_by(Issue.priority, Issue.created_at.desc())

    # Limit
    session.query(User).limit(10)

    # Offset (pagination)
    session.query(User).offset(20).limit(10)  # Page 3 (20-30)
```

## Relationships

```python
with get_session() as session:
    # One-to-Many
    user = session.query(User).first()
    for sess in user.crawl_sessions:  # Access sessions
        print(sess.session_uuid)

    # Many-to-One (reverse)
    sess = session.query(CrawlSession).first()
    print(sess.user.username)  # Access user

    # Many-to-Many (via association)
    for si in sess.session_issues:  # Access association
        issue = si.issue  # Access issue
        print(f"{issue.issue_id}: order {si.crawl_order}")
```

## Joins

```python
with get_session() as session:
    # Inner join
    session.query(User, CrawlSession).join(
        CrawlSession, User.user_id == CrawlSession.user_id
    )

    # Left outer join
    session.query(User, CrawlSession).outerjoin(
        CrawlSession
    )

    # Multiple joins
    session.query(CrawlSession).join(
        SessionIssue
    ).join(
        Issue
    )
```

## Aggregation

```python
with get_session() as session:
    from sqlalchemy import func

    # Count
    total = session.query(func.count(User.user_id)).scalar()

    # Group by
    by_product = session.query(
        Issue.product,
        func.count(Issue.issue_pk)
    ).group_by(Issue.product).all()

    # Average/Min/Max
    session.query(
        func.avg(CrawlSession.duration_seconds),
        func.min(CrawlSession.duration_seconds),
        func.max(CrawlSession.duration_seconds)
    ).first()
```

## JSONB

```python
with get_session() as session:
    # Access field
    sessions = session.query(CrawlSession).filter(
        CrawlSession.session_metadata['version'].astext == '1.0'
    )

    # Check key exists
    sessions = session.query(CrawlSession).filter(
        CrawlSession.session_metadata.has_key('version')
    )

    # Contains
    sessions = session.query(CrawlSession).filter(
        CrawlSession.session_metadata.contains({'version': '1.0'})
    )
```

## Transactions

```python
with get_session() as session:
    try:
        # Multiple operations
        session.add(User(...))
        session.add(CrawlSession(...))
        session.commit()  # Commit all
    except Exception as e:
        # Automatic rollback
        raise
```

## Bulk Operations

```python
with get_session() as session:
    # Bulk insert
    issues = [Issue(...) for i in range(100)]
    session.bulk_save_objects(issues)
    session.commit()

    # Bulk update
    session.query(Issue).filter(
        Issue.status == 'New'
    ).update({Issue.status: 'Open'})
    session.commit()

    # Bulk delete
    session.query(SessionError).filter(
        SessionError.severity == 'info'
    ).delete()
    session.commit()
```

## Eager Loading

```python
with get_session() as session:
    from sqlalchemy.orm import joinedload

    # Load relationships in single query
    issues = session.query(Issue).options(
        joinedload(Issue.comments),
        joinedload(Issue.history)
    ).all()

    # Access without additional queries
    for issue in issues:
        print(f"{len(issue.comments)} comments")
```

## Common Queries

### Get User with Sessions

```python
with get_session() as session:
    user = session.query(User).filter_by(username='yijae.shin').first()
    print(f"Total sessions: {len(user.crawl_sessions)}")
```

### Get Session with Issues

```python
with get_session(user_id=2) as session:
    sess = session.query(CrawlSession).filter_by(
        session_uuid='abc-123'
    ).first()

    for si in sess.session_issues:
        print(f"{si.issue.issue_id}: {si.issue.title}")
```

### Search Issues

```python
with get_session() as session:
    issues = session.query(Issue).filter(
        Issue.product == 'OpenFrame',
        Issue.status == 'Open'
    ).order_by(Issue.priority.desc()).all()
```

### Get User Stats

```python
with get_session(user_id=2) as session:
    from sqlalchemy import func

    stats = session.query(
        func.count(CrawlSession.session_id),
        func.sum(CrawlSession.issues_crawled),
        func.avg(CrawlSession.duration_seconds)
    ).filter(CrawlSession.user_id == 2).first()

    print(f"Sessions: {stats[0]}, Issues: {stats[1]}, Avg: {stats[2]}")
```

### Recent Activity

```python
with get_session(user_id=2) as session:
    recent = session.query(CrawlSession).order_by(
        CrawlSession.started_at.desc()
    ).limit(10).all()

    for sess in recent:
        print(f"{sess.started_at}: {sess.product} ({sess.status})")
```

## Row Level Security

### With User Context

```python
# Automatic RLS filtering
with get_session(user_id=2) as session:
    # Only returns sessions for user 2
    sessions = session.query(CrawlSession).all()
```

### Manual Context

```python
with get_session() as session:
    from sqlalchemy import text

    # Set user context
    session.execute(text("SELECT ims.set_current_user(:user_id)"), {"user_id": 2})

    # Now queries filtered
    sessions = session.query(CrawlSession).all()
```

## Best Practices

### ✅ Do

```python
# Use context managers
with get_session() as session:
    # Work here

# Use relationships
user.crawl_sessions

# Eager load when needed
.options(joinedload(Issue.comments))

# Set user context for RLS
with get_session(user_id=2) as session:
```

### ❌ Don't

```python
# Don't forget to close sessions
session = get_session()  # Missing 'with'

# Don't use manual joins for relationships
session.query(User, CrawlSession).join(...)  # Use user.crawl_sessions

# Don't cause N+1 queries
for issue in issues:
    issue.comments  # Triggers query each time!

# Don't forget user context
with get_session() as session:  # RLS may block!
```

## Debugging

### Print SQL

```python
from database import get_db_manager

# Enable SQL echo
db = get_db_manager()
db.config.echo = True  # Prints all SQL queries
```

### Inspect Query

```python
with get_session() as session:
    query = session.query(User).filter(User.role == 'admin')
    print(str(query))  # Show SQL
```

### Check Loaded Attributes

```python
from sqlalchemy import inspect

user = session.query(User).first()
insp = inspect(user)
print(insp.unloaded)  # Show unloaded relationships
```

## Error Handling

```python
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

with get_session() as session:
    try:
        session.add(User(username='duplicate'))
        session.commit()
    except IntegrityError as e:
        print(f"Duplicate or constraint error: {e}")
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
```

## Reference

- Full Documentation: `database/ORM_USAGE_GUIDE.md`
- Models: `database/models.py`
- Database Setup: `database/README.md`
- SQLAlchemy Docs: https://docs.sqlalchemy.org/en/20/
