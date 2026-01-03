"""
Analyze why Issue 347863 was not included in search results
"""
import sys
import io
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Check found issues
print("=" * 80)
print("검색된 이슈 분석 (Query: +TPETIME +error)")
print("=" * 80)

session_folder = Path('data/crawl_sessions/OpenFrame_TPETIME_error_20260103_115229')

found_issues = []
for json_file in sorted(session_folder.glob('*.json')):
    with open(json_file, encoding='utf-8') as f:
        issue = json.load(f)

    title = issue['title']
    desc = issue['description']
    issue_id = issue['issue_id']

    # Check keywords
    has_error_en = 'error' in (title + desc).lower()
    has_error_kr = '에러' in (title + desc)
    has_tpetime = 'TPETIME' in (title + desc)

    found_issues.append({
        'id': issue_id,
        'title': title,
        'error_en': has_error_en,
        'error_kr': has_error_kr,
        'tpetime': has_tpetime
    })

print(f"\n총 {len(found_issues)}개 이슈 발견\n")

for i, issue in enumerate(found_issues, 1):
    print(f"[{i}] Issue {issue['id']}")
    print(f"    Title: {issue['title'][:70]}...")
    print(f"    TPETIME: {issue['tpetime']}, error(영): {issue['error_en']}, 에러(한): {issue['error_kr']}")
    print()

# Now check Issue 347863
print("\n" + "=" * 80)
print("Issue 347863 분석 (검색 결과에 누락됨)")
print("=" * 80)

issue_347863_file = Path('data/crawl_sessions/OpenFrame_TPETIME_20260103_045204/347863_20260103_045306.json')
if issue_347863_file.exists():
    with open(issue_347863_file, encoding='utf-8') as f:
        issue = json.load(f)

    title = issue['title']
    desc = issue['description'][:500]  # First 500 chars

    has_error_en = 'error' in (title + desc).lower()
    has_error_kr = '에러' in (title + desc)
    has_tpetime = 'TPETIME' in (title + desc)

    print(f"Title: {title}")
    print(f"\nDescription (처음 500자):")
    print(desc)
    print(f"\n키워드 매칭:")
    print(f"  - TPETIME: {has_tpetime} ✓" if has_tpetime else f"  - TPETIME: {has_tpetime} ✗")
    print(f"  - error (영어): {has_error_en} {'✓' if has_error_en else '✗'}")
    print(f"  - 에러 (한글): {has_error_kr} ✓" if has_error_kr else f"  - 에러 (한글): {has_error_kr} ✗")

    print("\n" + "=" * 80)
    print("결론")
    print("=" * 80)

    if has_tpetime and has_error_kr and not has_error_en:
        print("✗ Issue 347863은 'TPETIME'과 '에러'(한글)는 포함하지만")
        print("  'error'(영어)는 포함하지 않습니다.")
        print("\n원인: IMS 검색 시스템이 'error'(영어)와 '에러'(한글)를")
        print("      다른 키워드로 인식하여 매칭하지 않았습니다.")
        print("\n해결책: 검색 쿼리를 '+TPETIME +에러'로 변경하거나")
        print("        '+TPETIME' 단독으로 검색 필요")
else:
    print("Issue 347863 파일을 찾을 수 없습니다.")

# Summary
print("\n" + "=" * 80)
print("통계")
print("=" * 80)
error_en_count = sum(1 for issue in found_issues if issue['error_en'])
error_kr_count = sum(1 for issue in found_issues if issue['error_kr'])

print(f"검색된 10개 이슈 중:")
print(f"  - 'error' (영어) 포함: {error_en_count}개")
print(f"  - '에러' (한글) 포함: {error_kr_count}개")
