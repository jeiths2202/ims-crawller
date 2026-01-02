# IMS Crawler Usage Guide

Comprehensive guide with real-world scenarios and best practices for crawling IMS issues.

## Table of Contents

- [Quick Start](#quick-start)
- [Natural Language Queries](#natural-language-queries)
- [Advanced Search Patterns](#advanced-search-patterns)
- [Multi-Language Support](#multi-language-support)
- [Batch Processing](#batch-processing)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Basic OR Search
Find issues mentioning either "connection" OR "timeout":
```bash
python main.py crawl -p "Tibero" -k "connection timeout" -m 50
```

### Basic AND Search
Find issues with BOTH "error" AND "crash":
```bash
python main.py crawl -p "OpenFrame" -k "+error +crash" -m 50
```

### Exact Phrase Search
Find exact phrase "out of memory":
```bash
python main.py crawl -p "JEUS" -k "'out of memory'" -m 100
```

## Natural Language Queries

The IMS Crawler now supports natural language input in **English, Korean, and Japanese**. Simply type your query naturally, and it will be parsed into IMS syntax.

### English Examples

**Simple AND query:**
```bash
python main.py crawl -p "Tibero" -k "find error and crash" -m 50
# Parsed to: +error +crash
```

**OR query with verbs:**
```bash
python main.py crawl -p "JEUS" -k "show connection or timeout issues" -m 50
# Parsed to: connection timeout
```

**Exact phrase:**
```bash
python main.py crawl -p "OpenFrame" -k "exact phrase 'database lock'" -m 50
# Parsed to: 'database lock'
```

**Mixed query:**
```bash
python main.py crawl -p "Tibero" -k "find memory and performance or crash" -m 50
# Parsed to: +memory +performance crash
```

### Korean Examples (한국어)

**AND 검색:**
```bash
python main.py crawl -p "Tibero" -k "에러와 크래시 찾아줘" -m 50
# Parsed to: +에러 +크래시
```

**OR 검색:**
```bash
python main.py crawl -p "JEUS" -k "연결 또는 타임아웃 보여줘" -m 50
# Parsed to: 연결 타임아웃
```

**정확한 구문:**
```bash
python main.py crawl -p "OpenFrame" -k "정확히 '메모리 부족'" -m 50
# Parsed to: '메모리 부족'
```

**복합 쿼리:**
```bash
python main.py crawl -p "Tibero" -k "데이터베이스와 성능 또는 장애" -m 50
# Parsed to: +데이터베이스 +성능 장애
```

### Japanese Examples (日本語)

**AND検索:**
```bash
python main.py crawl -p "Tibero" -k "エラーとクラッシュを検索" -m 50
# Parsed to: +エラー +クラッシュ
```

**OR検索:**
```bash
python main.py crawl -p "JEUS" -k "接続またはタイムアウト" -m 50
# Parsed to: 接続 タイムアウト
```

**完全一致:**
```bash
python main.py crawl -p "OpenFrame" -k "正確に 'メモリ不足'" -m 50
# Parsed to: 'メモリ不足'
```

**複合クエリ:**
```bash
python main.py crawl -p "Tibero" -k "データベースと性能または障害" -m 50
# Parsed to: +データベース +性能 障害
```

## Advanced Search Patterns

### Combining Multiple Operators

**Database errors with exact phrase:**
```bash
python main.py crawl -p "Tibero" -k "database +error +'connection timeout'" -m 50
# Finds: database AND error AND exact phrase "connection timeout"
```

**Product-specific issue patterns:**
```bash
python main.py crawl -p "OpenFrame" -k "OFCOBOL OFPLI +compile +error" -m 100
# Finds: (OFCOBOL OR OFPLI) AND compile AND error
```

**Performance investigation:**
```bash
python main.py crawl -p "JEUS" -k "slow performance +'thread pool' +timeout" -m 50
# Finds: slow AND performance AND "thread pool" AND timeout
```

### Issue Number Search

**Single issue:**
```bash
python main.py crawl -p "OpenFrame" -k "348115" -m 1
```

**Multiple issues (OR):**
```bash
python main.py crawl -p "Tibero" -k "348115 347878 346525" -m 10
```

**Required issue number:**
```bash
python main.py crawl -p "JEUS" -k "+5213 error" -m 20
# Finds: Issue 5213 AND error
```

### Related Issues Crawling

**Crawl with related issues:**
```bash
python main.py crawl -p "OpenFrame" -k "core dump" --crawl-related --max-depth 2 -m 50
# Crawls matching issues + their related issues (up to depth 2)
```

**Deep related crawl:**
```bash
python main.py crawl -p "Tibero" -k "replication failure" --crawl-related --max-depth 3 -m 20
# Deeper crawl for comprehensive investigation
```

## Multi-Language Support

### Automatic Language Detection

The crawler automatically detects the language of your query:

- **English**: Uses word boundaries and English keywords
- **Korean**: Detects Hangul characters (가-힣)
- **Japanese**: Detects Hiragana, Katakana, Kanji (ぁ-んァ-ヶ一-龯)

### Mixed Language Queries

**English + Korean:**
```bash
python main.py crawl -p "Tibero" -k "database 에러 찾기" -m 50
# Language detected: Korean (prioritized)
```

**English + Japanese:**
```bash
python main.py crawl -p "JEUS" -k "timeout エラーを検索" -m 50
# Language detected: Japanese (prioritized)
```

### Parsing Confidence

The parser provides confidence scores:
- **>90%**: High confidence (simple AND/OR/PHRASE queries)
- **80-90%**: Medium confidence (mixed queries)
- **<80%**: Low confidence (complex or ambiguous queries)

**Review low-confidence results:**
The crawler shows parsing results and asks for confirmation if confidence < 80%.

## Batch Processing

### Skip Confirmation (Automated Scripts)

For batch processing or automation, skip the confirmation prompt:

```bash
python main.py crawl -p "Tibero" -k "find error and crash" --no-confirm -m 100
```

**Use cases:**
- Scheduled crawls via cron jobs
- Automated data collection pipelines
- CI/CD integration
- Bulk issue analysis

### Disable LLM Fallback (Rules-Only)

For faster processing without LLM overhead:

```bash
python main.py crawl -p "JEUS" -k "show connection errors" --no-llm -m 50
```

**When to use:**
- Simple queries with high rule-based confidence
- Performance-critical scenarios
- Environments without Ollama installed
- High-volume batch processing

### Combined Batch Flags

```bash
python main.py crawl -p "OpenFrame" -k "find memory leak" --no-confirm --no-llm -m 200
# Fast automated crawling without prompts or LLM
```

## Performance Optimization

### Query Optimization

**Use IMS syntax directly (fastest):**
```bash
python main.py crawl -p "Tibero" -k "+error +crash" -m 50
# No parsing needed, immediate execution
```

**Use --no-llm for simple queries:**
```bash
python main.py crawl -p "JEUS" -k "find timeout" --no-llm -m 50
# Rules-only parsing, no LLM overhead
```

**Limit results appropriately:**
```bash
python main.py crawl -p "OpenFrame" -k "error" -m 20
# Smaller result sets = faster crawling
```

### Output Management

**Custom output directory:**
```bash
python main.py crawl -p "Tibero" -k "performance" -m 50 -o "./results/tibero"
```

**Browser mode (debugging):**
```bash
python main.py crawl -p "JEUS" -k "error" -m 10 --no-headless
# Shows browser window for debugging
```

## Real-World Scenarios

### Scenario 1: Investigation of Production Crash

**Goal:** Find all crash-related issues for Tibero database

```bash
# Step 1: Broad search for crashes
python main.py crawl -p "Tibero" -k "crash core dump abnormal termination" -m 100

# Step 2: Focus on specific error codes
python main.py crawl -p "Tibero" -k "+crash +'ORA-600'" -m 50

# Step 3: Crawl related issues for root cause analysis
python main.py crawl -p "Tibero" -k "crash" --crawl-related --max-depth 2 -m 30
```

### Scenario 2: Performance Troubleshooting

**Goal:** Identify performance bottlenecks in JEUS application server

```bash
# Step 1: General performance issues
python main.py crawl -p "JEUS" -k "find slow and performance" -m 100

# Step 2: Thread-related performance
python main.py crawl -p "JEUS" -k "+'thread pool' +timeout +performance" -m 50

# Step 3: Memory performance issues
python main.py crawl -p "JEUS" -k "memory leak +'out of memory' +performance" -m 50
```

### Scenario 3: Multi-Language Support Team

**Goal:** Team members search in their native languages

**English team member:**
```bash
python main.py crawl -p "OpenFrame" -k "find compilation errors" -m 50
```

**Korean team member:**
```bash
python main.py crawl -p "OpenFrame" -k "컴파일 에러 찾아줘" -m 50
```

**Japanese team member:**
```bash
python main.py crawl -p "OpenFrame" -k "コンパイルエラーを検索" -m 50
```

All three queries parse to the same IMS syntax: `+compilation +errors`

### Scenario 4: Automated Daily Reports

**Goal:** Generate daily reports of critical issues

**Cron job script:**
```bash
#!/bin/bash
# Daily critical issues report

# Tibero critical errors
python main.py crawl -p "Tibero" \
    -k "+critical +error" \
    --no-confirm \
    --no-llm \
    -m 100 \
    -o "./reports/tibero/$(date +%Y%m%d)"

# JEUS critical errors
python main.py crawl -p "JEUS" \
    -k "+critical +error" \
    --no-confirm \
    --no-llm \
    -m 100 \
    -o "./reports/jeus/$(date +%Y%m%d)"

# OpenFrame critical errors
python main.py crawl -p "OpenFrame" \
    -k "+critical +error" \
    --no-confirm \
    --no-llm \
    -m 100 \
    -o "./reports/openframe/$(date +%Y%m%d)"
```

### Scenario 5: Knowledge Base Building

**Goal:** Build comprehensive knowledge base for specific error patterns

```bash
# Network errors
python main.py crawl -p "Tibero" \
    -k "connection timeout network +'cannot connect'" \
    --crawl-related \
    --max-depth 2 \
    -m 200 \
    -o "./kb/network-errors"

# Memory errors
python main.py crawl -p "JEUS" \
    -k "memory leak +'out of memory' OOM" \
    --crawl-related \
    --max-depth 2 \
    -m 200 \
    -o "./kb/memory-errors"

# Authentication errors
python main.py crawl -p "OpenFrame" \
    -k "authentication login +'access denied'" \
    --crawl-related \
    --max-depth 2 \
    -m 200 \
    -o "./kb/auth-errors"
```

## Troubleshooting

### Natural Language Parsing Issues

**Problem:** Query parsed incorrectly

**Solution 1:** Review parsing result and confirm/cancel
```bash
python main.py crawl -p "Tibero" -k "find error and crash" -m 50
# Review the parsing table, confirm or cancel
```

**Solution 2:** Use IMS syntax directly
```bash
python main.py crawl -p "Tibero" -k "+error +crash" -m 50
# Direct IMS syntax, no parsing needed
```

**Solution 3:** Simplify your natural language query
```bash
# Complex (may parse incorrectly):
"find all database connection timeout errors and authentication failures"

# Simplified (better parsing):
"database connection timeout authentication"
# Or use IMS syntax: "+database +connection +timeout +authentication"
```

### LLM Fallback Issues

**Problem:** LLM server not available

**Check Ollama status:**
```bash
# Check if Ollama is running
ollama list

# Start Ollama server
ollama serve

# Pull the model if missing
ollama pull gemma:2b
```

**Workaround:** Use rules-only mode
```bash
python main.py crawl -p "Tibero" -k "find error" --no-llm -m 50
```

### Low Confidence Warnings

**Problem:** Parser shows low confidence (<80%)

**What it means:**
- The query is complex or ambiguous
- Rule-based parsing may not be accurate
- LLM fallback activated (if enabled)

**Recommendations:**
1. Review the parsed query carefully
2. Simplify your natural language
3. Use IMS syntax for precise control
4. Enable LLM fallback for better accuracy

### Performance Issues

**Problem:** Crawling is slow

**Solutions:**

1. **Reduce result count:**
```bash
python main.py crawl -p "Tibero" -k "error" -m 20  # Instead of -m 200
```

2. **Disable related issue crawling:**
```bash
python main.py crawl -p "JEUS" -k "error" -m 50  # Without --crawl-related
```

3. **Use rules-only mode:**
```bash
python main.py crawl -p "OpenFrame" -k "find timeout" --no-llm -m 50
```

4. **Use IMS syntax directly:**
```bash
python main.py crawl -p "Tibero" -k "+error +crash" -m 50
```

## Best Practices

### 1. Start Broad, Then Narrow

```bash
# Step 1: Broad search
python main.py crawl -p "Tibero" -k "error" -m 100

# Step 2: Analyze results, then narrow
python main.py crawl -p "Tibero" -k "+error +connection" -m 50

# Step 3: Focus on specific pattern
python main.py crawl -p "Tibero" -k "+error +connection +'timeout exceeded'" -m 20
```

### 2. Use Appropriate Language

- **Natural language:** Quick exploration, ad-hoc searches
- **IMS syntax:** Precise control, batch processing, automation

### 3. Leverage Multi-Language Support

- Let team members use their native language
- All queries normalize to same IMS syntax
- Consistent results across languages

### 4. Optimize for Your Use Case

**Interactive exploration:**
```bash
python main.py crawl -p "JEUS" -k "find performance issues" -m 50
# Review results, confirm parsing
```

**Automated batch:**
```bash
python main.py crawl -p "JEUS" -k "+performance +slow" --no-confirm --no-llm -m 100
# Fast, automated, no prompts
```

### 5. Monitor Parsing Confidence

- High confidence (>90%): Trust the parsing
- Medium confidence (80-90%): Review the result
- Low confidence (<80%): Consider simplifying or using IMS syntax

### 6. Use Related Issue Crawling Wisely

**Good use cases:**
- Root cause analysis
- Knowledge base building
- Comprehensive issue investigation

**Avoid when:**
- Quick searches
- Performance is critical
- Result set is already large

## Summary

The IMS Crawler provides flexible query options:

1. **IMS Syntax:** Direct, precise, fastest
2. **Natural Language (English):** Conversational, intuitive
3. **Natural Language (Korean/Japanese):** Native language support
4. **LLM Fallback:** Handles complex queries automatically

Choose the right approach for your use case, and leverage batch processing flags for automation!
