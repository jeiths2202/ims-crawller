"""
Test NL detection for the problematic query
"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from crawler.nl_parser import is_ims_syntax, NaturalLanguageParser

# Test query
query = "TPETIME error의 발생원인과 대응방안에 대해서 알려줘"

print(f"Query: {query}")
print(f"Is IMS Syntax? {is_ims_syntax(query)}")

# If detected as natural language, parse it
if not is_ims_syntax(query):
    print("\nDetected as Natural Language - Parsing...")
    parser = NaturalLanguageParser()
    result = parser.parse(query)

    print(f"\nParsing Result:")
    print(f"  IMS Query: {result.ims_query}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Method: {result.method}")
    print(f"  Language: {result.language}")
    print(f"  Explanation: {result.explanation}")
else:
    print("\nDetected as IMS Syntax - Will be used as-is")
    print(f"  Query will be: {query}")
