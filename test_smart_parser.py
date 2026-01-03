"""Test smart priority-based parser"""
from crawler.nl_parser import NaturalLanguageParser

parser = NaturalLanguageParser()

# Test case 1: TPETIME query (Korean)
query1 = "OpenFrame에서 TPETIME 에러 발생 원인과 대응방안"
result1 = parser.parse(query1)

print("=" * 60)
print("Test 1: Korean natural language with priority")
print("=" * 60)
print(f"Original: {query1}")
print(f"Parsed: {result1.ims_query}")
print(f"Language: {result1.language}")
print(f"Confidence: {result1.confidence:.1%}")
print(f"Explanation: {result1.explanation}")
print()

# Test case 2: Simple English
query2 = "OpenFrame TPETIME error timeout"
result2 = parser.parse(query2)

print("=" * 60)
print("Test 2: English keywords")
print("=" * 60)
print(f"Original: {query2}")
print(f"Parsed: {result2.ims_query}")
print(f"Language: {result2.language}")
print(f"Confidence: {result2.confidence:.1%}")
print(f"Explanation: {result2.explanation}")
print()

# Test case 3: Only high priority
query3 = "TPETIME SVC99 DYNALLOC"
result3 = parser.parse(query3)

print("=" * 60)
print("Test 3: Only technical terms")
print("=" * 60)
print(f"Original: {query3}")
print(f"Parsed: {result3.ims_query}")
print(f"Language: {result3.language}")
print(f"Confidence: {result3.confidence:.1%}")
print(f"Explanation: {result3.explanation}")
