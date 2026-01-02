"""
Quick integration test for CLI natural language parsing

This test verifies the NL parser integration without requiring IMS credentials
"""
from crawler.nl_parser import NaturalLanguageParser, is_ims_syntax, ParsingError


def test_cli_workflow():
    """Simulate the CLI workflow for natural language queries"""

    print("="*60)
    print("CLI Integration Test - Natural Language Parser")
    print("="*60)
    print()

    test_cases = [
        {
            'name': 'IMS Syntax (Passthrough)',
            'query': '+error +crash',
            'expected_type': 'ims_syntax',
        },
        {
            'name': 'Natural Language AND Query',
            'query': 'find error and crash',
            'expected_type': 'natural_language',
            'expected_output': '+error +crash',
        },
        {
            'name': 'Natural Language OR Query',
            'query': 'show connection or timeout',
            'expected_type': 'natural_language',
            'expected_output': 'connection timeout',
        },
        {
            'name': 'Issue Number (Passthrough)',
            'query': '348115',
            'expected_type': 'ims_syntax',
        },
        {
            'name': 'Complex Natural Language',
            'query': 'find database connection timeout error',
            'expected_type': 'natural_language',
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"[TEST] {test['name']}")
        print(f"  Input: \"{test['query']}\"")

        try:
            # Step 1: Detect IMS syntax
            if is_ims_syntax(test['query']):
                # IMS syntax - passthrough
                final_query = test['query']
                print(f"  -> IMS syntax detected")
                print(f"  -> Final Query: \"{final_query}\"")

                if test['expected_type'] == 'ims_syntax':
                    print("  -> PASS")
                    passed += 1
                else:
                    print("  -> FAIL: Expected natural language parsing")
                    failed += 1

            else:
                # Natural language - parse
                parser = NaturalLanguageParser()
                result = parser.parse(test['query'])

                print(f"  -> Natural language detected")
                print(f"  -> Parsed: \"{result.ims_query}\"")
                print(f"  -> Confidence: {result.confidence:.0%}")
                print(f"  -> Language: {result.language}")

                if test['expected_type'] == 'natural_language':
                    if 'expected_output' in test:
                        if result.ims_query == test['expected_output']:
                            print("  -> PASS")
                            passed += 1
                        else:
                            print(f"  -> FAIL: Expected \"{test['expected_output']}\"")
                            failed += 1
                    else:
                        print("  -> PASS (output not specified)")
                        passed += 1
                else:
                    print("  -> FAIL: Expected IMS syntax passthrough")
                    failed += 1

        except ParsingError as e:
            print(f"  -> ERROR: {e}")
            failed += 1

        print()

    # Summary
    print("="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = test_cli_workflow()
    exit(0 if success else 1)
