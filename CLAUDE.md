# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IMS Crawler - A Python-based web crawler for extracting structured data from custom Issue Management Systems (IMS) for knowledge base integration and RAG (Retrieval-Augmented Generation) systems.

**Phase 1 (Current)**: Python CLI tool with core crawling functionality
**Phase 2 (Future)**: Web application with UI and scheduled crawling

## Technology Stack

- **Language**: Python 3.10+
- **Web Automation**: Playwright (browser automation)
- **HTML Parsing**: BeautifulSoup4
- **CLI**: Click + Rich (terminal UI)
- **Document Processing**: PyPDF2, pdfplumber, python-docx
- **Configuration**: python-dotenv
- **Testing**: pytest + pytest-playwright

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with IMS credentials
```

### Running
```bash
# Check configuration
python main.py config

# Crawl issues
python main.py crawl --product "Tibero" --keywords "error" --max-results 50

# Test search query
python main.py test-query "connection +error"
```

### Testing
```bash
# Run unit tests
pytest tests/ -v

# Run specific test
pytest tests/test_search.py -v
```

## Architecture

```
CLI Interface (main.py)
    ↓
Config Manager (config/settings.py)
    ↓
IMS Scraper (crawler/ims_scraper.py)
    ├─> Auth Manager (crawler/auth.py)
    ├─> Search Query Builder (crawler/search.py)
    ├─> IMS Parser (crawler/parser.py)
    └─> Attachment Processor (crawler/attachment_processor.py)
    ↓
JSON Output (data/issues/)
Attachments (data/attachments/)
```

## Customization Guide for Your IMS

**IMPORTANT**: The crawler includes placeholder selectors that MUST be customized for your specific IMS system.

### Files Requiring Customization

1. **crawler/auth.py** - Login selectors and verification logic
2. **crawler/ims_scraper.py** - Search page URL and result selectors
3. **crawler/parser.py** - All issue detail page selectors

### Customization Steps

1. Run crawler with `--no-headless` flag to see browser
2. Use browser DevTools to inspect HTML elements
3. Update CSS selectors in code (marked with `# TODO: Update selector`)
4. Test incrementally: login → search → parse single issue → full crawl

## IMS Search Syntax

The system supports IMS-specific search operators:
- **OR**: Space-delimited (e.g., "Tmax Tibero")
- **AND**: Plus prefix (e.g., "+error +timeout")
- **Exact phrase**: Quoted (e.g., '"connection timeout"')
- **Combined**: Mix all operators

## Code Organization

- `config/` - Configuration management
- `crawler/` - Core crawling modules
  - `auth.py` - Authentication & session management
  - `search.py` - IMS search query builder
  - `ims_scraper.py` - Main scraper orchestration
  - `parser.py` - HTML parsing & data extraction
  - `attachment_processor.py` - File download & text extraction
- `tests/` - Unit tests
- `data/` - Output directory (gitignored)
- `main.py` - CLI interface

## Data Output

Each crawled issue produces:
1. JSON file with complete issue data (`data/issues/IMS-XXXXX_timestamp.json`)
2. Downloaded attachments (`data/attachments/IMS-XXXXX/`)
3. Extracted text from attachments (`.txt` files alongside originals)

## Notes for Future Development

### Phase 2: Web Application
- Flask/FastAPI backend
- React/Vue frontend
- Real-time crawl progress
- Scheduled crawling
- Database storage (PostgreSQL)

### RAG Integration
- Output JSON is ready for vector DB ingestion
- Recommended flow:
  1. Crawl issues → JSON
  2. Preprocess text (concat title + desc + comments + attachments)
  3. Generate embeddings
  4. Store in Vector DB (Chroma/Qdrant/Pinecone)
  5. Query with LLM for troubleshooting

### Performance Enhancements
- Parallel crawling (multi-threaded)
- Incremental updates (only new/modified issues)
- Caching strategies
- Retry logic with exponential backoff
