# 🕷️ IMS Crawler

A Python-based web crawler for extracting structured data from custom IMS (Issue Management Systems) for knowledge base integration and troubleshooting support.

## 📋 Overview

This crawler enables systematic extraction of issues, comments, attachments, and history from IMS systems, preparing data for integration with RAG (Retrieval-Augmented Generation) systems and LLM-powered troubleshooting guides.

### Key Features

- ✅ **Web Scraping**: Automated browser-based crawling using Playwright
- 🔐 **Authentication**: Session management with automatic re-login on timeout
- 🔍 **Advanced Search**: Support for IMS-specific search syntax (OR, AND, exact phrase)
- 🗣️ **Natural Language Parsing**: Conversational queries in English, Korean, Japanese (Phase 2)
- 🤖 **LLM Fallback**: Optional Ollama integration for complex query parsing (Phase 3)
- 📦 **Attachment Processing**: Downloads and extracts text from PDFs, Word docs, images
- 📊 **Structured Output**: JSON format with complete issue metadata
- 🎯 **User-Driven**: Crawl on-demand based on product and keyword filters
- 🚀 **CLI Interface**: Rich terminal UI with progress tracking and batch mode (Phase 4)

**📖 See [USAGE_GUIDE.md](USAGE_GUIDE.md) for comprehensive examples and real-world scenarios**

## 🏗️ Architecture

```
User Input (Product + Keywords)
    ↓
┌─────────────────────────────────────┐
│      Authentication Manager         │
│   (Login + Session Management)      │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│      Search Query Builder           │
│   (IMS Syntax: OR/AND/Exact)        │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│      Main Scraper Engine            │
│   (Playwright Browser Automation)   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│      IMS Page Parser                │
│   (Extract: Title, Desc, Comments,  │
│    History, Attachments, Metadata)  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│      Attachment Processor           │
│   (Download + Text Extraction)      │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│      JSON Exporter                  │
│   (Structured Issue Data)           │
└─────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Git

### Installation

1. **Clone the repository**
```bash
cd web-crawler
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers**
```bash
playwright install chromium
```

5. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your IMS credentials and URL
```

### Configuration

Edit `.env` file:

```env
# IMS Configuration
IMS_BASE_URL=https://your-ims-system.com
IMS_USERNAME=your_username
IMS_PASSWORD=your_password

# Crawler Settings
MAX_CONCURRENT_REQUESTS=5
DEFAULT_MAX_RESULTS=100
DOWNLOAD_ATTACHMENTS=true

# Output Settings
OUTPUT_DIR=data/issues
ATTACHMENTS_DIR=data/attachments
```

### Basic Usage

**Check configuration:**
```bash
python main.py config
```

**Crawl issues:**
```bash
python main.py crawl --product "Tibero" --keywords "connection +error" --max-results 50
```

**Test search query:**
```bash
python main.py test-query "timeout crash +error"
```

## 🗣️ Natural Language Search (NEW!)

You can now use natural language instead of IMS syntax! The crawler automatically detects and converts natural language queries.

### Quick Examples

**English Natural Language**:
```bash
# AND query: find issues with both error AND crash
python main.py crawl -p "Tibero" -k "find error and crash" -m 50
# Automatically converted to: +error +crash

# OR query: find issues with connection OR timeout
python main.py crawl -p "OpenFrame" -k "show connection or timeout" -m 50
# Automatically converted to: connection timeout

# Complex query
python main.py crawl -p "JEUS" -k "find database error and crash or timeout" -m 50
# Automatically converted to: +database +error +crash timeout
```

### How It Works

1. **Automatic Detection**: The crawler detects if your query is natural language or IMS syntax
2. **Intelligent Parsing**: Converts natural language to IMS syntax using rule-based parsing
3. **User Confirmation**: Shows you the parsed query and asks for confirmation
4. **High Confidence**: 90%+ accuracy for simple queries

### Batch Mode (Skip Confirmation)

Use `--no-confirm` flag to skip the confirmation prompt for automation:

```bash
python main.py crawl -p "Tibero" -k "find error and crash" --no-confirm -m 50
```

### Performance Mode (Rules-Only)

Use `--no-llm` flag to disable LLM fallback for faster processing:

```bash
python main.py crawl -p "JEUS" -k "show connection errors" --no-llm -m 50
```

**Combined flags for automated batch processing:**
```bash
python main.py crawl -p "OpenFrame" -k "find memory leak" --no-confirm --no-llm -m 200
```

**Korean Natural Language**:
```bash
# AND query: 에러와 크래시가 모두 포함된 이슈 찾기
python main.py crawl -p "Tibero" -k "에러와 크래시 찾아줘" -m 50
# Automatically converted to: +에러 +크래시

# OR query: 연결 또는 타임아웃 이슈 찾기
python main.py crawl -p "OpenFrame" -k "연결 또는 타임아웃 보여줘" -m 50
# Automatically converted to: 연결 타임아웃

# Complex query
python main.py crawl -p "JEUS" -k "데이터베이스 에러 그리고 크래시 또는 타임아웃" -m 50
# Automatically converted to: +데이터베이스 +에러 +크래시 +타임아웃
```

**Japanese Natural Language**:
```bash
# AND query: エラーとクラッシュの両方を含む問題を検索
python main.py crawl -p "Tibero" -k "エラーとクラッシュを検索" -m 50
# Automatically converted to: +エラー +クラッシュ

# OR query: 接続またはタイムアウトの問題を検索
python main.py crawl -p "OpenFrame" -k "接続またはタイムアウト" -m 50
# Automatically converted to: 接続 タイムアウト

# Complex query
python main.py crawl -p "JEUS" -k "データベース エラー および クラッシュ または タイムアウト" -m 50
# Automatically converted to: +データベース +エラー +クラッシュ +タイムアウト
```

### Supported Languages

- ✅ **English** (Phase 2 - Available Now)
- ✅ **Korean** (Phase 2 - Available Now)
- ✅ **Japanese** (Phase 2 - Available Now)

### LLM Fallback (Phase 3 - Optional)

For complex queries that rule-based parsing can't handle confidently, you can enable optional LLM fallback using Ollama:

```bash
# Enable LLM fallback in .env
USE_LLM=true
LLM_MODEL=gemma:2b
```

**When does LLM activate?**
- Natural language query detected
- Rule-based confidence < 0.7
- Ollama server is running

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download model (1.4GB, lightweight & fast)
ollama pull gemma:2b

# Start server
ollama serve
```

**See [OLLAMA_SETUP.md](OLLAMA_SETUP.md) for complete installation guide**

**Note:** LLM is completely optional. The crawler works perfectly fine with rules-only parsing.

---

## 📖 IMS Search Syntax

> 📚 **See [SEARCH_GUIDE.md](SEARCH_GUIDE.md) for complete search syntax guide with examples**

The crawler also supports direct IMS-native search syntax. You can use IMS syntax directly if you prefer manual control.

### 1. OR Search (Space Delimiter)
Multiple keywords separated by spaces are searched with OR logic.

```bash
python main.py crawl -p "Tibero" -k "Tmax Tibero"
# Finds: Issues containing Tmax OR Tibero
```

**Rule**: Use a space as a delimiter between keywords.

### 2. AND Search (+ Operator)
To require a specific word in results, use the plus operator (+) before the word with **no space** between them.

```bash
python main.py crawl -p "OpenFrame" -k "IMS +error"
# Finds: Issues containing IMS AND must contain error

python main.py crawl -p "Tibero" -k "+connection +timeout"
# Finds: Issues that must contain both connection AND timeout
```

**Rule**: `+keyword` requires that word to appear. No space between + and the word.

### 3. Exact Phrase Search (Single Quotation Marks)
To search for an exact word or phrase, enclose it in single quotation marks (' ').

```bash
python main.py crawl -p "JEUS" -k "'error log'"
# Finds: Exact phrase "error log"

python main.py crawl -p "Tibero" -k "'out of memory'"
# Finds: Exact phrase "out of memory"
```

**Rule**: Use single quotes (' ') around exact phrases.

### 4. Combined Search (+ and ' ')
The plus operator (+) and single quotation marks (' ') can be used together.

```bash
python main.py crawl -p "OpenFrame" -k "Tmax 'error log' +Tibero"
# Finds: (Tmax OR 'error log') AND must contain Tibero

python main.py crawl -p "Tibero" -k "database +error +'connection timeout'"
# Finds: database AND error AND exact phrase "connection timeout"

python main.py crawl -p "JEUS" -k "Tmax '+error log'"
# Finds: Tmax AND exact phrase "error log"
```

**Rule**: Combine operators for complex queries.

### 5. Issue Number Search
Search by specific issue numbers.

```bash
python main.py crawl -p "OpenFrame" -k "348115"
# Finds: Issue number 348115

python main.py crawl -p "OpenFrame" -k "348115 347878 346525"
# Finds: Issue 348115 OR 347878 OR 346525

python main.py crawl -p "Tibero" -k "+348115"
# Finds: Required issue number 348115
```

**Rule**: Issue numbers can be searched directly or with + for required match.

### 6. Keyword Highlighting
Found keywords are automatically highlighted in the IMS search results to make them easy to identify.

### 7. Complete Examples

```bash
# Simple OR search
python main.py crawl -p "Tibero" -k "connection timeout crash" -m 50

# Multiple required terms (AND)
python main.py crawl -p "OpenFrame" -k "+error +timeout +crash" -m 30

# Exact phrase only
python main.py crawl -p "JEUS" -k "'out of memory'" -m 20

# Complex combination
python main.py crawl -p "Tibero" -k "database error +crash +'connection timeout'" -m 50
# Finds: (database OR error) AND crash AND exact phrase "connection timeout"

# Multiple issue numbers
python main.py crawl -p "OpenFrame" -k "348115 347878" -m 10

# Crawl with related issues (new feature)
python main.py crawl -p "OpenFrame" -k "5213" --crawl-related --max-depth 2 -m 10
# Finds issue 5213 and automatically crawls all related issues up to depth 2
```

### 8. Related Issues Crawling (NEW)

Automatically crawl related issues referenced in the `related_issues` field:

```bash
# Enable related issue crawling
python main.py crawl -p "OpenFrame" -k "error" --crawl-related

# Set maximum depth (default: 2)
python main.py crawl -p "OpenFrame" -k "error" --crawl-related --max-depth 3

# Example: Crawl issue and all its related issues
python main.py crawl -p "OpenFrame" -k "348115" --crawl-related --max-depth 1
```

**Features**:
- Automatically prevents infinite loops (tracks crawled issues)
- Parallel processing: 30% of search results are processed concurrently
- Each related issue is saved as a separate JSON file
- Configurable depth to control how deep to follow related issues

---

## 🎯 Advanced Features (NEW!)

### 1. Query History and Favorites

Track all your queries automatically and save frequently used searches as favorites.

**View query history:**
```bash
# Show last 20 queries
python main.py history

# Filter by product
python main.py history --product "Tibero"

# Filter by language
python main.py history --language "ko"

# Show more results
python main.py history --limit 50
```

**Manage favorites:**
```bash
# List all favorites
python main.py favorites --list

# Add last query to favorites
python main.py favorites --add -1

# Add specific query from history (by index)
python main.py favorites --add 5

# Remove favorite
python main.py favorites --remove 0
```

**View statistics:**
```bash
# Show query statistics
python main.py stats

# Export statistics to JSON
python main.py stats --export stats_report.json
```

**Features**:
- ✅ Automatic history tracking for every query
- ✅ Favorite query management
- ✅ Filter by product, language, or parsing method
- ✅ Query statistics and success rates
- ✅ Export history to JSON/CSV

### 2. Interactive Query Builder

Build queries step-by-step with a guided terminal UI.

**Launch interactive builder:**
```bash
python main.py build
```

**Features**:
- ✅ Step-by-step guided query construction
- ✅ Load queries from favorites or history
- ✅ Real-time query preview as you type
- ✅ Product selection menu
- ✅ Query type selection (AND/OR/PHRASE/MIXED/DIRECT)
- ✅ Automatic query execution after confirmation

**Query Types Available**:
- **AND Query**: All terms required (`+term1 +term2`)
- **OR Query**: Any term matches (`term1 term2`)
- **Exact Phrase**: Exact match only (`'exact phrase'`)
- **Mixed Query**: Combination of operators
- **Direct IMS Syntax**: Raw IMS syntax (advanced users)

### 3. Advanced Analytics

Comprehensive analytics on query patterns, performance, and parsing accuracy.

**View analytics dashboard:**
```bash
# Full analytics dashboard
python main.py analytics

# Summary view (less detailed)
python main.py analytics --format summary

# Analyze trends for specific period
python main.py analytics --days 30

# Export comprehensive report
python main.py analytics --export report.json
```

**Available Metrics**:

1. **Performance Metrics**
   - Execution time statistics (avg, min, max, median)
   - Confidence score analysis
   - Success rate and result quality

2. **Usage Patterns**
   - Peak usage hours and days
   - Most popular products
   - Language distribution
   - Activity rate over time

3. **Parsing Accuracy**
   - Performance by parsing method (rules/llm/direct)
   - Confidence scores by method
   - Success rate comparison

4. **Query Complexity Analysis**
   - Simple vs medium vs complex query breakdown
   - Execution time by complexity
   - Complexity distribution

5. **Trend Analysis**
   - Query volume trends (7-day, 30-day)
   - Daily breakdown with metrics
   - Growth rate calculation

**Example Output**:
```
📊 Advanced Analytics Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Queries Analyzed: 127

⚡ Performance Metrics
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric              ┃ Value                    ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Avg Execution Time  │ 2.34s                    │
│ Avg Confidence      │ 87.5%                    │
│ Success Rate        │ 94.1%                    │
└─────────────────────┴──────────────────────────┘

📈 Usage Patterns
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Pattern          ┃ Details                         ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Peak Hour        │ 14:00-14:59 (23 queries)       │
│ Peak Day         │ Wednesday (31 queries)          │
│ Top Products     │ Tibero (45), OpenFrame (38)    │
└──────────────────┴─────────────────────────────────┘
```

---

## 📁 Output Structure

### JSON Output Format

Each crawled issue is saved as a separate JSON file:

```json
{
  "issue_id": "IMS-12345",
  "title": "Connection timeout error in Tibero",
  "description": "Detailed description of the issue...",
  "product": "Tibero",
  "status": "Resolved",
  "priority": "High",
  "created_date": "2024-01-15",
  "updated_date": "2024-01-20",
  "reporter": "john.doe",
  "assignee": "jane.smith",
  "comments": [
    {
      "author": "john.doe",
      "date": "2024-01-15",
      "content": "Initial comment..."
    }
  ],
  "history": [
    {
      "user": "jane.smith",
      "date": "2024-01-16",
      "action": "Status changed",
      "details": "From Open to In Progress"
    }
  ],
  "attachments": [
    {
      "name": "error.log",
      "url": "/attachments/12345/error.log",
      "size": "15 KB",
      "local_path": "data/attachments/IMS-12345/error.log",
      "extracted_text": "Preview of extracted text..."
    }
  ],
  "metadata": {},
  "url": "https://ims.example.com/issue/IMS-12345",
  "crawled_at": "2024-01-21T10:30:00"
}
```

### Directory Structure

```
data/
├── issues/                 # Crawled issue JSON files
│   ├── IMS-12345_20240121_103000.json
│   ├── IMS-12346_20240121_103015.json
│   └── ...
└── attachments/           # Downloaded attachments
    ├── IMS-12345/
    │   ├── error.log
    │   ├── error.log.txt  # Extracted text
    │   └── screenshot.png
    └── IMS-12346/
        └── ...
```

## 🔧 Advanced Usage

### Custom Output Directory

```bash
python main.py crawl \
  --product "JEUS" \
  --keywords "memory +leak" \
  --max-results 100 \
  --output-dir "./custom_output"
```

### Run with Visible Browser (Debug Mode)

```bash
python main.py crawl \
  --product "Tibero" \
  --keywords "error" \
  --max-results 10 \
  --no-headless
```

### Batch Processing

Create a shell script for multiple queries:

```bash
#!/bin/bash
# batch_crawl.sh

products=("Tibero" "JEUS" "WebtoB")
keywords=("error" "timeout" "crash")

for product in "${products[@]}"; do
  for keyword in "${keywords[@]}"; do
    echo "Crawling: $product - $keyword"
    python main.py crawl -p "$product" -k "+$keyword" -m 50
  done
done
```

## 🛠️ Customization Guide

### Adapting to Your IMS System

The crawler includes **TODO** markers in the code where customization is required based on your specific IMS system:

#### 1. Authentication (`crawler/auth.py`)

Update login selectors:
```python
# Update these selectors based on your IMS login page
page.fill('input[name="username"]', self.username)  # Update selector
page.fill('input[name="password"]', self.password)  # Update selector
page.click('button[type="submit"]')  # Update selector
```

#### 2. Search Execution (`crawler/ims_scraper.py`)

Update search page selectors:
```python
# Update search URL
search_url = f"{self.base_url}/search"  # Update URL

# Update search input selector
self.page.fill('input[name="search"]', query)  # Update selector

# Update result list selector
result_elements = self.page.query_selector_all('.issue-link')  # Update selector
```

#### 3. Issue Parsing (`crawler/parser.py`)

Update all extraction selectors based on your IMS HTML structure:
```python
# Example: Update title extraction
def _extract_title(self, page: Page) -> str:
    element = page.query_selector('.issue-title')  # Update this selector
    return element.text_content().strip() if element else ''
```

### Testing Your Customizations

1. **Run with visible browser:**
```bash
python main.py crawl -p "Test" -k "test" -m 1 --no-headless
```

2. **Use browser DevTools to inspect elements and find correct selectors**

3. **Test incrementally** - verify login, search, then full crawl

## 📊 Data Processing Pipeline

### Recommended Workflow for RAG Integration

```
1. Crawl IMS Issues
   └─> python main.py crawl -p "Product" -k "keywords" -m 1000

2. Process JSON Files
   └─> Load all JSON from data/issues/
   └─> Combine into single dataset

3. Text Preprocessing
   └─> Concatenate: title + description + comments
   └─> Include attachment text extracts
   └─> Clean and normalize text

4. Embedding Generation
   └─> Use sentence-transformers or OpenAI embeddings
   └─> Store in Vector DB (Chroma, Qdrant, Pinecone)

5. RAG System Integration
   └─> Query: User troubleshooting question
   └─> Retrieve: Top-K similar issues from Vector DB
   └─> Generate: LLM response based on retrieved context
```

## 🐛 Troubleshooting

### Common Issues

**Authentication fails:**
- Verify credentials in `.env`
- Check if IMS has CAPTCHA or 2FA (not currently supported)
- Run with `--no-headless` to see what's happening

**Search returns no results:**
- Test query syntax with `python main.py test-query "your query"`
- Verify product name is correct
- Check IMS manually to confirm issues exist

**Playwright timeout errors:**
- Increase timeout in `config/settings.py`: `BROWSER_TIMEOUT = 60000`
- Check network connectivity
- IMS might be slow - add delays

**Missing attachments:**
- Set `DOWNLOAD_ATTACHMENTS=true` in `.env`
- Check disk space
- Verify download permissions

## 📝 Project Structure

```
web-crawler/
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration management
├── crawler/
│   ├── __init__.py
│   ├── auth.py               # Authentication & session management
│   ├── search.py             # IMS search query builder
│   ├── ims_scraper.py        # Main scraper engine
│   ├── parser.py             # HTML parsing & data extraction
│   └── attachment_processor.py  # Attachment download & text extraction
├── data/                     # Output directory (gitignored)
│   ├── issues/               # Crawled JSON files
│   └── attachments/          # Downloaded files
├── tests/                    # Unit tests
├── .env.example              # Environment template
├── .gitignore
├── main.py                   # CLI interface
├── requirements.txt
├── CLAUDE.md                 # Project guidance for Claude
├── plan.md                   # Project plan (Korean)
└── README.md                 # This file
```

## 🔮 Future Enhancements

### Phase 2: Web Application
- [ ] Flask/FastAPI web interface
- [ ] Real-time crawl progress dashboard
- [ ] Scheduled crawling (cron-like)
- [ ] Multi-user support
- [ ] RAG query interface

### Additional Features
- [ ] Incremental crawling (only new/updated issues)
- [ ] Database storage (PostgreSQL)
- [ ] Advanced filtering (date range, status, priority)
- [ ] Export formats (CSV, Excel)
- [ ] Parallel crawling for faster processing
- [ ] Retry logic for failed downloads
- [ ] Email notifications on completion

## 📄 License

[Specify your license here]

## 🤝 Contributing

[Contribution guidelines if open source]

## 📧 Contact

[Your contact information]

---

**Built with ❤️ for IMS knowledge extraction and RAG integration**
