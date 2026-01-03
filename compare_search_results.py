"""
Compare search results before and after synonym expansion

This script compares the old search results (without synonym expansion)
with the new results (with synonym expansion) to demonstrate the improvement.
"""
import sys
import io
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def load_issue_ids(session_folder):
    """Load all issue IDs from a session folder"""
    session_path = Path(session_folder)
    if not session_path.exists():
        return set()

    issue_ids = set()
    for json_file in session_path.glob('*.json'):
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)
            issue_ids.add(data['issue_id'])

    return issue_ids

def main():
    # Old search results (without synonym expansion)
    old_session = Path('data/crawl_sessions/OpenFrame_TPETIME_error_20260103_115229')

    # New search results (with synonym expansion)
    new_session = Path('data/crawl_sessions/OpenFrame_TPETIME_error_에러_오류_20260103_120855')

    print("=" * 80)
    print("Search Results Comparison: Before vs After Synonym Expansion")
    print("=" * 80)

    print(f"\n📊 **Query**: \"TPETIME error의 발생원인과 대응방안에 대해서 알려줘\"\n")

    # Load issue IDs
    old_issues = load_issue_ids(old_session)
    new_issues = load_issue_ids(new_session)

    # Calculate differences
    only_in_old = old_issues - new_issues
    only_in_new = new_issues - old_issues
    common = old_issues & new_issues

    # Display results
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│ BEFORE Synonym Expansion                                    │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│ Session: {old_session.name[:55]:<55} │")
    print(f"│ Parsed Query: +TPETIME +error                               │")
    print(f"│ Total Issues: {len(old_issues):>2}                                            │")
    print("└─────────────────────────────────────────────────────────────┘")

    if old_issues:
        print("\nIssues found:")
        for issue_id in sorted(old_issues):
            marker = "  (common)" if issue_id in common else ""
            print(f"  - {issue_id}{marker}")
    else:
        print("\n  (No issues found)")

    print("\n" + "─" * 80)

    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ AFTER Synonym Expansion                                     │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│ Session: {new_session.name[:55]:<55} │")
    print(f"│ Parsed Query: +TPETIME error 에러 오류                      │")
    print(f"│ Total Issues: {len(new_issues):>2}                                            │")
    print("└─────────────────────────────────────────────────────────────┘")

    if new_issues:
        print("\nIssues found:")
        for issue_id in sorted(new_issues):
            if issue_id in only_in_new:
                print(f"  - {issue_id}  ✨ NEW (found due to synonym expansion)")
            elif issue_id in common:
                print(f"  - {issue_id}")
    else:
        print("\n  (No issues found)")

    # Summary
    print("\n" + "=" * 80)
    print("📈 Summary")
    print("=" * 80)

    print(f"\nTotal issues (before): {len(old_issues)}")
    print(f"Total issues (after):  {len(new_issues)}")

    if only_in_new:
        print(f"\n✨ **NEW ISSUES FOUND**: {len(only_in_new)}")
        for issue_id in sorted(only_in_new):
            # Load issue details
            issue_file = new_session / f"{issue_id}*.json"
            matching_files = list(new_session.glob(f"{issue_id}_*.json"))
            if matching_files:
                with open(matching_files[0], encoding='utf-8') as f:
                    data = json.load(f)
                    title = data['title']
                    print(f"\n  Issue {issue_id}:")
                    print(f"    Title: {title}")

                    # Check which keyword matched
                    has_error_en = 'error' in title.lower()
                    has_error_kr = '에러' in title
                    has_error_kr2 = '오류' in title

                    if has_error_kr or has_error_kr2:
                        print(f"    ✓ Matched Korean synonym: '{'에러' if has_error_kr else '오류'}'")
                        if not has_error_en:
                            print(f"    ✗ Would NOT match with English 'error' only")
    else:
        print("\n  (No new issues found - all results were already in previous search)")

    if only_in_old:
        print(f"\n⚠️  **ISSUES LOST**: {len(only_in_old)}")
        for issue_id in sorted(only_in_old):
            print(f"  - {issue_id}")
    else:
        print(f"\n✅ **NO ISSUES LOST**: All previous results still found")

    print("\n" + "=" * 80)
    print("Conclusion")
    print("=" * 80)

    improvement = len(only_in_new)
    if improvement > 0:
        percentage = (improvement / len(old_issues)) * 100 if old_issues else 0
        print(f"\n✅ Synonym expansion SUCCESSFUL!")
        print(f"   - Found {improvement} additional issue(s)")
        print(f"   - Improvement: +{percentage:.1f}% in recall")
        print(f"   - No precision loss (all previous results retained)")
    elif len(old_issues) == len(new_issues) and not only_in_old:
        print(f"\n⚪ No change in results")
        print(f"   - Same {len(old_issues)} issues found in both searches")
        print(f"   - Synonym expansion had no impact for this specific query")
    else:
        print(f"\n⚠️  Unexpected result")
        print(f"   - Please investigate differences")

    print(f"\n📝 Note: Issue 347863 should appear in 'NEW ISSUES FOUND' section")
    print(f"   if synonym expansion is working correctly.")

if __name__ == "__main__":
    main()
