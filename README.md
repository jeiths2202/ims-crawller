# 🕷️ IMS Crawler

A Python-based web crawler for extracting structured data from custom IMS (Issue Management Systems) for knowledge base integration and troubleshooting support.

## 📋 Overview

This crawler enables systematic extraction of issues, comments, attachments, and history from IMS systems, preparing data for integration with RAG (Retrieval-Augmented Generation) systems and LLM-powered troubleshooting guides.

### Key Features

- ✅ **Web Scraping**: Automated browser-based crawling using Playwright
- 🔐 **Authentication**: Session management with automatic re-login on timeout
- 🔍 **Advanced Search**: Support for IMS-specific search syntax (OR, AND, exact phrase)
- 📦 **Attachment Processing**: Downloads and extracts text from PDFs, Word docs, images
- 📊 **Structured Output**: JSON format with complete issue metadata
- 🎯 **User-Driven**: Crawl on-demand based on product and keyword filters
- 🚀 **CLI Interface**: Rich terminal UI with progress tracking

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

## 📖 IMS Search Syntax

The crawler supports the following IMS-specific search operators:

### 1. OR Search (Space Delimiter)
```bash
python main.py crawl -p "Tibero" -k "Tmax Tibero"
# Finds: Tmax OR Tibero
```

### 2. AND Search (+ Operator)
```bash
python main.py crawl -p "Tibero" -k "IMS +error"
# Finds: IMS AND error
```

### 3. Exact Phrase Search (Quotation Marks)
```bash
python main.py crawl -p "Tibero" -k '"connection timeout"'
# Finds: Exact phrase "connection timeout"
```

### 4. Complex Queries (Combination)
```bash
python main.py crawl -p "Tibero" -k 'timeout crash +error +"system failure"'
# Finds: (timeout OR crash) AND error AND "system failure"
```

### 5. Issue Number Search
```bash
python main.py crawl -p "Tibero" -k "+IMS-12345"
# Finds: Specific issue number
```

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
