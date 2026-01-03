"""
Test various Korean query patterns with intent keyword filtering
"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from crawler.nl_parser import NaturalLanguageParser

# Test cases with various Korean patterns
test_cases = [
    # Original problematic query
    {
        'query': 'TPETIME error의 발생원인과 대응방안에 대해서 알려줘',
        'expected': '+TPETIME +error',
        'description': 'Intent keywords filtering (발생원인, 대응방안)'
    },

    # Cause inquiry patterns
    {
        'query': 'TPETIME이 발생하는 원인',
        'expected': '+TPETIME',
        'description': 'Cause inquiry - 원인 filtering'
    },
    {
        'query': 'timeout error 발생 이유',
        'expected': 'timeout error',
        'description': 'Cause inquiry - 이유 filtering'
    },

    # Solution inquiry patterns
    {
        'query': 'TPETIME 해결방법',
        'expected': '+TPETIME',
        'description': 'Solution inquiry - 해결방법 filtering'
    },
    {
        'query': 'connection timeout 처리방안',
        'expected': 'connection timeout',
        'description': 'Solution inquiry - 처리방안 filtering'
    },

    # Information request patterns
    {
        'query': 'OpenFrame TPETIME 가이드',
        'expected': '+OpenFrame +TPETIME',
        'description': 'Info request - 가이드 filtering'
    },
    {
        'query': 'batch job failure 정보',
        'expected': 'batch job failure',
        'description': 'Info request - 정보 filtering'
    },

    # Mixed patterns
    {
        'query': 'RC16 에러의 원인과 해결책을 알려줘',
        'expected': '+RC16',
        'description': 'Mixed intent keywords (원인, 해결책) + verb filtering'
    },
    {
        'query': 'OpenFrame에서 TPETIME 발생 시 조치사항',
        'expected': '+OpenFrame +TPETIME',
        'description': 'Intent keyword 조치사항 filtering'
    },

    # Should NOT filter (meaningful keywords)
    {
        'query': 'batch job error',
        'expected': 'batch job error',
        'description': 'All meaningful keywords - no filtering'
    },
    {
        'query': 'OpenFrame TPETIME timeout',
        'expected': '+OpenFrame +TPETIME timeout',
        'description': 'Technical terms - no filtering'
    },
]

# Run tests
parser = NaturalLanguageParser()
print("=" * 80)
print("Korean Intent Keyword Filtering Test")
print("=" * 80)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    query = test['query']
    expected = test['expected']
    description = test['description']

    result = parser.parse(query)
    actual = result.ims_query

    status = "✓ PASS" if actual == expected else "✗ FAIL"
    if actual == expected:
        passed += 1
    else:
        failed += 1

    print(f"\n[Test {i}] {status}")
    print(f"Description: {description}")
    print(f"Query:      {query}")
    print(f"Expected:   {expected}")
    print(f"Actual:     {actual}")

    if actual != expected:
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Method:     {result.method}")
        print(f"Language:   {result.language}")

print("\n" + "=" * 80)
print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 80)

# Exit with appropriate code
sys.exit(0 if failed == 0 else 1)
