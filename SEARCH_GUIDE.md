# IMS Search Syntax Guide

This guide explains how to use IMS search operators in the web-crawler CLI.

## Quick Reference

| Syntax | Description | Example | Finds |
|--------|-------------|---------|-------|
| `keyword1 keyword2` | OR search | `"Tmax Tibero"` | Tmax OR Tibero |
| `+keyword` | AND search (required) | `"IMS +error"` | IMS AND error |
| `'exact phrase'` | Exact phrase | `"'error log'"` | Exact phrase "error log" |
| Combined | Mix operators | `"Tmax +error +'timeout'"` | Tmax AND error AND "timeout" |
| Issue number | Search by ID | `"348115"` | Issue #348115 |

## 1. OR Search (Space Delimiter)

**Syntax**: `keyword1 keyword2 keyword3`

Multiple keywords separated by spaces are searched with OR logic.

```bash
# Find issues containing Tmax OR Tibero
python main.py crawl -p "Tibero" -k "Tmax Tibero" -m 50

# Find connection OR timeout OR crash
python main.py crawl -p "OpenFrame" -k "connection timeout crash" -m 50
```

## 2. AND Search (+ Operator)

**Syntax**: `+keyword` (no space between + and keyword)

To require a specific word in all results, use the plus operator (+).

```bash
# Find issues containing error (required)
python main.py crawl -p "OpenFrame" -k "+error" -m 50

# Find issues with both connection AND timeout
python main.py crawl -p "Tibero" -k "+connection +timeout" -m 50

# Find IMS issues that must contain error
python main.py crawl -p "OpenFrame" -k "IMS +error" -m 50
```

⚠️ **Important**: No space between + and the keyword!
- ✅ Correct: `+error`
- ❌ Wrong: `+ error`

## 3. Exact Phrase Search (Single Quotes)

**Syntax**: `'exact phrase'`

To search for an exact word or phrase, enclose it in single quotation marks.

```bash
# Find exact phrase "error log"
python main.py crawl -p "JEUS" -k "'error log'" -m 50

# Find exact phrase "out of memory"
python main.py crawl -p "Tibero" -k "'out of memory'" -m 50

# Find exact phrase "connection timeout"
python main.py crawl -p "OpenFrame" -k "'connection timeout'" -m 50
```

⚠️ **Important**: Use single quotes (' '), not double quotes (" ")!

## 4. Combined Search

**Syntax**: Mix all operators

The plus operator (+) and single quotation marks (' ') can be used together.

```bash
# Tmax OR ('error log' AND Tibero)
python main.py crawl -p "OpenFrame" -k "Tmax 'error log' +Tibero" -m 50

# database AND error AND exact phrase "connection timeout"
python main.py crawl -p "Tibero" -k "database +error +'connection timeout'" -m 50

# Tmax AND exact phrase "error log"
python main.py crawl -p "JEUS" -k "Tmax '+error log'" -m 50

# (error OR crash) AND timeout AND exact phrase "system failure"
python main.py crawl -p "OpenFrame" -k "error crash +timeout +'system failure'" -m 50
```

## 5. Issue Number Search

**Syntax**: `issue_number` or `+issue_number`

Search by specific issue numbers.

```bash
# Find issue 348115
python main.py crawl -p "OpenFrame" -k "348115" -m 1

# Find multiple issues (OR)
python main.py crawl -p "OpenFrame" -k "348115 347878 346525" -m 10

# Find required issue number
python main.py crawl -p "Tibero" -k "+348115" -m 1
```

## 6. Real-World Examples

### Example 1: Find Critical Database Errors
```bash
python main.py crawl -p "Tibero" -k "database +error +critical" -m 50
```
Finds: Issues containing "database" that MUST have both "error" AND "critical"

### Example 2: Find Connection Timeout Issues
```bash
python main.py crawl -p "OpenFrame" -k "'connection timeout' +error" -m 50
```
Finds: Issues with exact phrase "connection timeout" that MUST have "error"

### Example 3: Find Multiple Product Issues
```bash
python main.py crawl -p "OpenFrame" -k "Tibero JEUS OpenFrame +crash" -m 50
```
Finds: Issues mentioning (Tibero OR JEUS OR OpenFrame) that MUST have "crash"

### Example 4: Find Out of Memory Errors
```bash
python main.py crawl -p "JEUS" -k "'out of memory' +'java.lang.OutOfMemoryError'" -m 50
```
Finds: Issues with exact phrase "out of memory" AND exact phrase "java.lang.OutOfMemoryError"

### Example 5: Find Performance Issues
```bash
python main.py crawl -p "Tibero" -k "slow performance +timeout +'response time'" -m 50
```
Finds: (slow OR performance) AND timeout AND exact phrase "response time"

## 7. Related Issues Crawling (NEW)

Automatically crawl related issues referenced in each issue.

```bash
# Basic usage: crawl issue and its related issues
python main.py crawl -p "OpenFrame" -k "348115" --crawl-related

# Set maximum depth (default: 2)
python main.py crawl -p "OpenFrame" -k "error" --crawl-related --max-depth 3 -m 10

# Find critical issues and all related issues
python main.py crawl -p "Tibero" -k "+critical +error" --crawl-related --max-depth 2 -m 20
```

**Features**:
- Automatically prevents infinite loops
- Parallel processing (30% of results processed concurrently)
- Each related issue saved as separate JSON file
- Configurable depth to control recursion

## 8. Tips & Best Practices

### ✅ DO:
- Use single quotes (' ') for exact phrases
- Use + with no space for required keywords
- Combine operators for precise searches
- Test your search query first with small `-m` value

### ❌ DON'T:
- Don't use double quotes for exact phrases (use single quotes)
- Don't put space between + and keyword
- Don't forget quotes for multi-word phrases
- Don't use too broad searches without limiting results

### 💡 Pro Tips:

1. **Start Narrow, Then Expand**
   ```bash
   # Start with specific required terms
   python main.py crawl -p "Tibero" -k "+error +connection +timeout" -m 10

   # If too few results, remove some + operators
   python main.py crawl -p "Tibero" -k "error connection +timeout" -m 50
   ```

2. **Use Issue Numbers for Precision**
   ```bash
   # When you know specific issues
   python main.py crawl -p "OpenFrame" -k "348115 347878" -m 10
   ```

3. **Combine with Related Crawling**
   ```bash
   # Find root issue and all related issues
   python main.py crawl -p "OpenFrame" -k "348115" --crawl-related --max-depth 2
   ```

4. **Test Search Queries**
   ```bash
   # Use small -m value to test
   python main.py crawl -p "Tibero" -k "your complex query" -m 5

   # If results are good, increase -m
   python main.py crawl -p "Tibero" -k "your complex query" -m 100
   ```

## 9. Troubleshooting

### No Results Found?
- Check if + operator has no space: `+error` not `+ error`
- Check if exact phrases use single quotes: `'error log'` not `"error log"`
- Try removing some + operators to broaden search
- Try OR search instead of AND search

### Too Many Results?
- Add more + operators to narrow search
- Use exact phrases for specific terms
- Reduce `-m` value to limit results
- Be more specific with keywords

### Search Query Not Working?
- Check for proper quote escaping in shell
- Use single quotes for exact phrases
- Verify no space between + and keyword
- Test with simpler query first

## 10. Getting Help

```bash
# Show CLI help
python main.py crawl --help

# Show all available commands
python main.py --help

# Check configuration
python main.py config
```

## Additional Resources

- See `README.md` for full documentation
- See `CLAUDE.md` for technical architecture
- See `QUICKSTART.md` for quick setup guide
