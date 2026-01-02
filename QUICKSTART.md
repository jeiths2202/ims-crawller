# 🚀 Quick Start Guide

## What Was Built

A complete **Phase 1 IMS Crawler** - a production-ready Python CLI tool that:
- Crawls your custom IMS system using browser automation
- Supports complex search queries (OR/AND/exact phrase)
- Extracts complete issue data (descriptions, comments, attachments, history)
- Downloads and processes attachments (PDFs, Word docs, images)
- Outputs structured JSON files ready for RAG integration

## ⚡ Get Started in 5 Minutes

### 1. Setup Environment

```bash
# Navigate to project
cd C:\Users\yijae.shin\Downloads\nim\web-crawler

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 2. Configure Credentials

```bash
# Copy example config
copy .env.example .env

# Edit .env file with your IMS details
notepad .env
```

Update these values in `.env`:
```env
IMS_BASE_URL=https://your-actual-ims-url.com
IMS_USERNAME=your_actual_username
IMS_PASSWORD=your_actual_password
```

### 3. Verify Setup

```bash
python main.py config
```

You should see a configuration table with ✅ checkmarks.

### 4. Run Your First Crawl (TEST MODE)

```bash
# Start with just 1 issue in visible browser mode to test
python main.py crawl --product "Tibero" --keywords "error" --max-results 1 --no-headless
```

**Watch what happens:**
- Browser opens automatically
- Attempts to login
- Searches for issues
- Extracts data

## ⚠️ IMPORTANT: Customization Required

The crawler will **NOT work out-of-the-box** because your IMS has unique HTML structure.

### What You Need to Customize

**Three files need updating with actual CSS selectors:**

#### 1. `crawler/auth.py` (Lines ~35-45)
Find your login form selectors using browser DevTools:
```python
# BEFORE (placeholder):
page.fill('input[name="username"]', self.username)  # Update selector
page.fill('input[name="password"]', self.password)  # Update selector
page.click('button[type="submit"]')  # Update selector

# AFTER (your actual selectors):
page.fill('#login-username', self.username)  # Your actual ID
page.fill('#login-password', self.password)  # Your actual ID
page.click('.btn-login')  # Your actual class
```

#### 2. `crawler/ims_scraper.py` (Lines ~150-180)
Find your search page structure:
```python
# Update search URL
search_url = f"{self.base_url}/search"  # Your actual search endpoint

# Update search input selector
self.page.fill('input[name="search"]', query)  # Your actual selector

# Update result link selector
result_elements = self.page.query_selector_all('.issue-link')  # Your actual selector
```

#### 3. `crawler/parser.py` (Multiple methods)
Update ALL `_extract_*` methods with your issue page structure:
```python
# Example: Update title extraction
def _extract_title(self, page: Page) -> str:
    element = page.query_selector('.issue-title')  # Update this
    return element.text_content().strip() if element else ''
```

### How to Find Selectors

1. **Run with visible browser:**
   ```bash
   python main.py crawl -p "Test" -k "test" -m 1 --no-headless
   ```

2. **While browser is open:**
   - Right-click on login fields → Inspect
   - Look for `id`, `class`, or `name` attributes
   - Copy the selector (e.g., `#username`, `.login-input`, `input[name="user"]`)

3. **Update code with actual selectors**

4. **Test again until login works**

## 📊 Expected Output

After successful customization and crawl:

```
data/
├── issues/
│   └── IMS-12345_20240121_103000.json  ← Complete issue data
└── attachments/
    └── IMS-12345/
        ├── error.log                   ← Downloaded file
        └── error.log.txt               ← Extracted text
```

## 🎯 Next Steps

### Immediate (Required)
1. ✅ Customize selectors in 3 files above
2. ✅ Test with 1 issue (`--max-results 1 --no-headless`)
3. ✅ Verify JSON output looks correct
4. ✅ Test with 10 issues
5. ✅ Scale up to hundreds/thousands

### Short-Term (This Week)
- Run production crawls for different products
- Build dataset for RAG integration
- Document any IMS-specific quirks discovered

### Long-Term (Phase 2)
- Web UI for easier access
- Scheduled crawling (daily/weekly)
- Direct RAG integration
- Database storage

## 🆘 Troubleshooting

### "Login Failed"
- Verify credentials in `.env`
- Check if IMS has CAPTCHA (not supported)
- Run with `--no-headless` to see what's happening
- Update selectors in `crawler/auth.py`

### "Search Returns Empty"
- Verify product name exactly matches IMS
- Test search manually in IMS first
- Update search selectors in `crawler/ims_scraper.py`

### "Can't Parse Issue Data"
- Issue page structure is different than expected
- Update ALL selectors in `crawler/parser.py`
- Test with browser DevTools

### Browser Crashes/Timeouts
- Increase timeout in `config/settings.py`: `BROWSER_TIMEOUT = 60000`
- Add delays between requests
- Check network connectivity

## 📚 Documentation

- **README.md** - Complete documentation
- **CLAUDE.md** - Technical architecture and customization guide
- **plan.md** - Project plan (Korean)
- **Code Comments** - All files have detailed comments with TODO markers

## 💬 Questions?

All code is documented with:
- Docstrings explaining what each function does
- TODO comments marking customization points
- Example values showing expected formats

Happy crawling! 🕷️
