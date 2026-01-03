"""
Test script for SQLAlchemy ORM models

This script tests all models by querying the database and displaying results.
"""

from database.db_config import get_db_manager, get_session
from database.models import (
    User, CrawlSession, Issue, SessionIssue, IssueComment,
    IssueHistory, Attachment, SearchQuery, SessionError,
    AnalyticsDaily, AnalyticsMonthly, AuditLog
)


def test_models():
    """Test all ORM models with sample queries"""

    print("=" * 70)
    print("Testing SQLAlchemy ORM Models")
    print("=" * 70)
    print()

    # Test connection
    db = get_db_manager()
    if not db.test_connection():
        print("[ERROR] Database connection failed!")
        return

    print("[OK] Database connection successful")
    print()

    # Test 1: Query Users
    print("-" * 70)
    print("Test 1: Query Users")
    print("-" * 70)

    with get_session() as session:
        users = session.query(User).all()
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"  - {user}")
            print(f"    Email: {user.email}")
            print(f"    Role: {user.role}")
            print(f"    Active: {user.is_active}")
            print(f"    Created: {user.created_at}")
        print()

    # Test 2: Query Crawl Sessions with User
    print("-" * 70)
    print("Test 2: Query Crawl Sessions with User Relationship")
    print("-" * 70)

    with get_session() as session:
        sessions = session.query(CrawlSession).all()
        print(f"Found {len(sessions)} sessions:")
        for sess in sessions:
            print(f"  - {sess}")
            print(f"    User: {sess.user.username}")
            print(f"    Product: {sess.product}")
            print(f"    Status: {sess.status}")
            print(f"    Query: {sess.original_query}")
            print(f"    Issues crawled: {sess.issues_crawled}")
        print()

    # Test 3: Query Issues with Relationships
    print("-" * 70)
    print("Test 3: Query Issues with Related Data")
    print("-" * 70)

    with get_session() as session:
        issues = session.query(Issue).all()
        print(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
            print(f"    Product: {issue.product}")
            print(f"    Status: {issue.status}")
            print(f"    Comments: {len(issue.comments)}")
            print(f"    History entries: {len(issue.history)}")
            print(f"    Attachments: {len(issue.attachments)}")
            print(f"    Crawled {issue.crawl_count} times")
        print()

    # Test 4: Query Session-Issue Associations
    print("-" * 70)
    print("Test 4: Session-Issue Associations")
    print("-" * 70)

    with get_session() as session:
        associations = session.query(SessionIssue).all()
        print(f"Found {len(associations)} session-issue associations:")
        for assoc in associations:
            print(f"  - {assoc}")
            print(f"    Session UUID: {assoc.session.session_uuid}")
            print(f"    Issue ID: {assoc.issue.issue_id}")
            print(f"    Crawl order: {assoc.crawl_order}")
            print(f"    Duration: {assoc.crawl_duration_ms}ms")
        print()

    # Test 5: Query Comments
    print("-" * 70)
    print("Test 5: Issue Comments")
    print("-" * 70)

    with get_session() as session:
        comments = session.query(IssueComment).all()
        print(f"Found {len(comments)} comments:")
        for comment in comments:
            print(f"  - {comment}")
            print(f"    Issue: {comment.issue.issue_id}")
            print(f"    Content: {comment.content[:100]}...")
        print()

    # Test 6: Query History
    print("-" * 70)
    print("Test 6: Issue History")
    print("-" * 70)

    with get_session() as session:
        history = session.query(IssueHistory).all()
        print(f"Found {len(history)} history entries:")
        for h in history:
            print(f"  - {h}")
            print(f"    Issue: {h.issue.issue_id}")
            print(f"    Change: {h.field_name} ({h.old_value} → {h.new_value})")
        print()

    # Test 7: Query Search Queries
    print("-" * 70)
    print("Test 7: Search Queries")
    print("-" * 70)

    with get_session() as session:
        queries = session.query(SearchQuery).all()
        print(f"Found {len(queries)} search queries:")
        for q in queries:
            print(f"  - {q}")
            print(f"    User: {q.user.username}")
            print(f"    Parsing method: {q.parsing_method}")
            print(f"    Confidence: {q.parsing_confidence}")
        print()

    # Test 8: Query Analytics Daily
    print("-" * 70)
    print("Test 8: Daily Analytics")
    print("-" * 70)

    with get_session() as session:
        daily_stats = session.query(AnalyticsDaily).all()
        print(f"Found {len(daily_stats)} daily analytics records:")
        for stat in daily_stats:
            print(f"  - {stat}")
            print(f"    Sessions: {stat.sessions_count}")
            print(f"    Success: {stat.successful_sessions}")
            print(f"    Failed: {stat.failed_sessions}")
        print()

    # Test 9: Query Audit Log
    print("-" * 70)
    print("Test 9: Audit Log")
    print("-" * 70)

    with get_session() as session:
        logs = session.query(AuditLog).all()
        print(f"Found {len(logs)} audit log entries:")
        for log in logs:
            print(f"  - {log}")
            if log.user:
                print(f"    User: {log.user.username}")
            print(f"    Resource: {log.resource_type}/{log.resource_id}")
        print()

    # Test 10: Complex Query with Joins
    print("-" * 70)
    print("Test 10: Complex Query - User with Sessions and Issues")
    print("-" * 70)

    with get_session() as session:
        user = session.query(User).filter_by(username='yijae.shin').first()
        if user:
            print(f"User: {user.username}")
            print(f"  Total sessions: {len(user.crawl_sessions)}")
            print(f"  Total queries: {len(user.search_queries)}")
            print(f"  Daily analytics records: {len(user.analytics_daily)}")

            for sess in user.crawl_sessions:
                print(f"\n  Session: {sess.session_uuid}")
                print(f"    Product: {sess.product}")
                print(f"    Issues: {len(sess.session_issues)}")
                for si in sess.session_issues:
                    print(f"      - {si.issue.issue_id}: {si.issue.title[:50]}...")
        print()

    print("=" * 70)
    print("[OK] All model tests completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    test_models()
