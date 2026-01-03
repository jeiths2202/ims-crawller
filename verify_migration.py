"""
Verify migration results and test UserRepository
"""
import sys
import io
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from crawler.user_repository import UserRepository

def main():
    print("=" * 80)
    print("🔍 Verifying Migration Results")
    print("=" * 80)

    # Initialize repository
    repo = UserRepository("yijae.shin")

    print(f"\n📂 User Repository: {repo.root}")
    print(f"   User ID: {repo.user_id}")

    # Get all sessions
    sessions = repo.get_sessions()
    print(f"\n📊 Sessions: {len(sessions)}")

    for i, session in enumerate(sessions, 1):
        print(f"\n[{i}] {session.session_id}")
        if session.metadata:
            config = session.metadata.search_config
            results = session.metadata.results
            print(f"    Product: {config.get('product')}")
            print(f"    Query: {config.get('original_query')}")
            print(f"    Language: {config.get('language')}")
            print(f"    Issues: {results.get('issues_crawled')}")
            print(f"    Created: {session.metadata.created_at}")
        else:
            print(f"    ⚠️  No metadata")

    # Get overall statistics
    print("\n" + "=" * 80)
    print("📈 Overall Statistics")
    print("=" * 80)

    stats = repo.get_stats()
    print(f"\nUser: {stats['user_id']}")
    print(f"Total Sessions: {stats['total_sessions']}")
    print(f"Total Issues Crawled: {stats['total_issues_crawled']}")
    print(f"Unique Issues: {stats['unique_issues']}")
    print(f"Total Attachments: {stats['total_attachments']}")

    print(f"\nSessions by Product:")
    for product, count in stats['sessions_by_product'].items():
        print(f"  {product}: {count}")

    # Test session queries
    print("\n" + "=" * 80)
    print("🔎 Testing Session Queries")
    print("=" * 80)

    # Find OpenFrame sessions
    openframe_sessions = repo.find_sessions_by_product("OpenFrame")
    print(f"\nOpenFrame sessions: {len(openframe_sessions)}")

    # Get latest session
    latest = repo.get_latest_session()
    if latest:
        print(f"\nLatest session: {latest.session_id}")
        if latest.metadata:
            print(f"  Query: {latest.metadata.search_config.get('original_query')}")
            print(f"  Issues: {len(latest.metadata.issue_ids)}")

    # Check directory structure
    print("\n" + "=" * 80)
    print("📁 Directory Structure")
    print("=" * 80)

    print(f"\n{repo.root}/")
    for subdir in sorted(repo.root.rglob("*")):
        if subdir.is_dir():
            rel_path = subdir.relative_to(repo.root)
            depth = len(rel_path.parts)
            if depth <= 2:  # Only show top 2 levels
                indent = "  " * depth
                print(f"{indent}├── {subdir.name}/")

    # Count files
    json_files = list(repo.root.rglob("*.json"))
    print(f"\n📄 Total JSON files: {len(json_files)}")

    print("\n✅ Migration verification complete!")

if __name__ == "__main__":
    main()
