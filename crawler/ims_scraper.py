"""
Main IMS Scraper Engine
Orchestrates the crawling process using Playwright
"""
import logging
import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from .auth import AuthManager, AuthenticationError
from .search import SearchQueryBuilder
from .parser import IMSParser
from .attachment_processor import AttachmentProcessor
from .db_integration import DatabaseSaver

logger = logging.getLogger(__name__)


class IMSScraper:
    """Main scraper class for IMS system"""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        output_dir: Path,
        attachments_dir: Path,
        headless: bool = True,
        cookie_file: Optional[str] = None,
        user_id: Optional[int] = None,
        use_database: bool = False
    ):
        self.base_url = base_url
        self.output_dir = output_dir
        self.attachments_dir = attachments_dir
        self.headless = headless
        self.cookie_file = cookie_file
        self.username = username
        self.password = password
        self.user_id = user_id
        self.use_database = use_database

        # Initialize components
        self.auth_manager = AuthManager(base_url, username, password, cookie_file=cookie_file)
        self.query_builder = SearchQueryBuilder()
        self.parser = IMSParser()
        self.attachment_processor = AttachmentProcessor(attachments_dir)

        # Initialize database saver if enabled
        self.db_saver = None
        if use_database and user_id:
            self.db_saver = DatabaseSaver(user_id, enabled=True)
            logger.info(f"Database integration enabled for user_id={user_id}")

        # Browser and page objects (initialized in context manager)
        self.browser: Optional[Browser] = None
        self.context: Optional[Any] = None
        self.page: Optional[Page] = None

        # Thread-safe lock for crawled issues tracking
        self._crawled_lock = threading.Lock()

        # Tracking for statistics
        self._crawl_start_time = None
        self._search_time_ms = None
        self._issue_times = []

    def __enter__(self):
        """Context manager entry - initialize browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup browser"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

    def crawl(
        self,
        product: str,
        keywords: str,
        max_results: int = 100,
        crawl_related: bool = False,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Main crawling method

        Args:
            product: Product name to filter by
            keywords: Search keywords (using IMS syntax)
            max_results: Maximum number of issues to crawl
            crawl_related: Whether to crawl related issues (default: False)
            max_depth: Maximum depth for related issue crawling (default: 2)

        Returns:
            List of crawled issue data as dictionaries
        """
        if not self.page:
            raise RuntimeError("Scraper not initialized. Use context manager (with statement)")

        # Start timing
        self._crawl_start_time = datetime.now(timezone.utc)
        search_start_time = None

        # Database session creation
        if self.db_saver:
            try:
                session_metadata = {
                    'crawler_version': '1.0.0',
                    'headless_mode': self.headless,
                    'max_depth': max_depth if crawl_related else 0
                }
                self.db_saver.create_session(
                    product=product,
                    original_query=keywords,
                    parsed_query=keywords,  # For now, same as original
                    max_results=max_results,
                    crawl_related=crawl_related,
                    session_metadata=session_metadata
                )
                logger.info(f"Created database session: {self.db_saver.session_uuid}")
            except Exception as e:
                logger.error(f"Failed to create database session: {e}")
                # Continue without database

        try:
            # Step 1: Authenticate
            logger.info("Step 1: Authenticating...")
            self.auth_manager.login(self.page, self.context)

            # Step 2: Build search query
            logger.info("Step 2: Building search query...")
            search_query = self.query_builder.build_query(keywords, product)
            logger.info(f"Search query: {search_query}")

            # Step 3: Execute search
            logger.info("Step 3: Executing search...")
            search_start_time = datetime.now(timezone.utc)
            issue_links = self._execute_search(search_query, max_results, product)
            search_end_time = datetime.now(timezone.utc)

            # Calculate search time
            self._search_time_ms = int((search_end_time - search_start_time).total_seconds() * 1000)
            logger.info(f"Found {len(issue_links)} issues to crawl (search took {self._search_time_ms}ms)")

            # Save search query to database
            if self.db_saver:
                try:
                    self.db_saver.save_search_query(
                        original_query=keywords,
                        parsed_query=search_query,
                        results_count=len(issue_links),
                        product=product,
                        parsing_method='rule_based',
                        parsing_confidence=1.0
                    )
                except Exception as e:
                    logger.error(f"Failed to save search query: {e}")

            # Step 4: Crawl each issue (and related issues if enabled)
            logger.info("Step 4: Crawling issues...")

            # Track crawled issues to avoid duplicates (thread-safe)
            crawled_issue_ids = set()
            all_crawled_issues = []

            # Calculate worker count: 30% of search results, min 1, max 10
            num_workers = max(1, min(10, int(len(issue_links) * 0.3)))
            logger.info(f"Using {num_workers} parallel workers for {len(issue_links)} issues")

            # Use ThreadPoolExecutor for parallel crawling
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all crawling tasks
                future_to_url = {}
                for idx, issue_url in enumerate(issue_links, 1):
                    future = executor.submit(
                        self._crawl_with_related_parallel,
                        issue_url,
                        crawled_issue_ids,
                        crawl_related,
                        0,
                        max_depth,
                        idx  # Pass crawl order
                    )
                    future_to_url[future] = (idx, issue_url)

                # Collect results as they complete
                for future in as_completed(future_to_url):
                    idx, issue_url = future_to_url[future]
                    try:
                        issues = future.result()
                        all_crawled_issues.extend(issues)
                        logger.info(f"Completed {idx}/{len(issue_links)}: {issue_url} (+{len(issues)-1} related)")
                    except Exception as e:
                        logger.error(f"Failed to crawl issue {issue_url}: {e}")
                        # Save error to database
                        if self.db_saver:
                            try:
                                self.db_saver.save_error(
                                    error_type='crawl_error',
                                    error_message=str(e),
                                    severity='error',
                                    error_detail={'issue_url': issue_url, 'index': idx}
                                )
                            except Exception as db_err:
                                logger.error(f"Failed to save error to database: {db_err}")
                        continue

            logger.info(f"Successfully crawled {len(all_crawled_issues)} issues (including related issues)")

            # Complete database session
            if self.db_saver:
                try:
                    crawl_end_time = datetime.now(timezone.utc)
                    total_crawl_time_ms = int((crawl_end_time - self._crawl_start_time).total_seconds() * 1000)
                    crawl_time_ms = total_crawl_time_ms - self._search_time_ms

                    # Calculate statistics
                    avg_issue_time_ms = int(sum(self._issue_times) / len(self._issue_times)) if self._issue_times else 0
                    attachments_downloaded = sum(
                        len(issue.get('attachments', [])) for issue in all_crawled_issues
                    )
                    related_issues = len(all_crawled_issues) - len(issue_links)

                    self.db_saver.complete_session(
                        status='completed',
                        total_issues_found=len(issue_links),
                        issues_crawled=len(all_crawled_issues),
                        attachments_downloaded=attachments_downloaded,
                        failed_issues=len(issue_links) - len([i for i in all_crawled_issues if i.get('crawl_order', 0) <= len(issue_links)]),
                        related_issues=related_issues,
                        search_time_ms=self._search_time_ms,
                        crawl_time_ms=crawl_time_ms,
                        avg_issue_time_ms=avg_issue_time_ms,
                        parallel_workers=num_workers
                    )
                    logger.info(f"Database session completed: {self.db_saver.session_uuid}")
                except Exception as e:
                    logger.error(f"Failed to complete database session: {e}")

            return all_crawled_issues

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            # Mark session as failed
            if self.db_saver:
                try:
                    self.db_saver.save_error(
                        error_type='authentication_error',
                        error_message=str(e),
                        severity='error'
                    )
                    self.db_saver.complete_session(status='failed')
                except Exception as db_err:
                    logger.error(f"Failed to save error to database: {db_err}")
            raise
        except Exception as e:
            logger.error(f"Crawling failed: {e}")
            # Mark session as failed
            if self.db_saver:
                try:
                    self.db_saver.save_error(
                        error_type='crawl_failure',
                        error_message=str(e),
                        severity='error'
                    )
                    self.db_saver.complete_session(status='failed')
                except Exception as db_err:
                    logger.error(f"Failed to save error to database: {db_err}")
            raise

    def _crawl_with_related_parallel(
        self,
        issue_url: str,
        crawled_issue_ids: set,
        crawl_related: bool = False,
        current_depth: int = 0,
        max_depth: int = 2,
        crawl_order: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl an issue and optionally its related issues recursively (parallel-safe version)
        Each thread creates its own browser context

        Args:
            issue_url: URL of the issue to crawl
            crawled_issue_ids: Set of already crawled issue IDs (to avoid duplicates)
            crawl_related: Whether to crawl related issues
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth
            crawl_order: Order in which this issue was crawled (for database)

        Returns:
            List of crawled issue data (main issue + related issues)
        """
        # Extract issue ID from URL
        import re
        match = re.search(r'issueId=(\d+)', issue_url)
        if not match:
            logger.warning(f"Could not extract issue ID from URL: {issue_url}")
            return []

        issue_id = match.group(1)

        # Thread-safe check and add
        with self._crawled_lock:
            if issue_id in crawled_issue_ids:
                logger.debug(f"Issue {issue_id} already crawled, skipping")
                return []
            crawled_issue_ids.add(issue_id)

        result = []

        # Create separate browser context for this thread
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=self.headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Create auth manager for this thread
            auth_manager = AuthManager(
                self.base_url,
                self.username,
                self.password,
                cookie_file=self.cookie_file
            )

            # Authenticate
            auth_manager.login(page, context)

            # Crawl this issue
            logger.info(f"[Depth {current_depth}] Crawling issue {issue_id}")
            issue_start_time = datetime.now(timezone.utc)
            issue_data = self._crawl_issue_detail_with_page(page, issue_url)
            issue_end_time = datetime.now(timezone.utc)

            # Calculate crawl duration
            crawl_duration_ms = int((issue_end_time - issue_start_time).total_seconds() * 1000)

            # Add crawl order to issue data
            if crawl_order:
                issue_data['crawl_order'] = crawl_order

            result.append(issue_data)

            # Save progress incrementally (thread-safe)
            self._save_issue(issue_data, crawl_order, crawl_duration_ms)

            # Crawl related issues if enabled and depth allows
            if crawl_related and current_depth < max_depth:
                related_issues = issue_data.get('related_issues', [])
                if related_issues:
                    logger.info(f"Found {len(related_issues)} related issues for issue {issue_id}")

                    for related in related_issues:
                        related_issue_no = related.get('issue_no', '')
                        if not related_issue_no:
                            continue

                        # Build URL for related issue
                        related_url = f"https://ims.tmaxsoft.com/tody/ims/issue/issueView.do?issueId={related_issue_no}&menuCode=issue_search"

                        # Recursively crawl related issue (will use its own browser context)
                        try:
                            related_results = self._crawl_with_related_parallel(
                                related_url,
                                crawled_issue_ids,
                                crawl_related=True,
                                current_depth=current_depth + 1,
                                max_depth=max_depth
                            )
                            result.extend(related_results)
                        except Exception as e:
                            logger.error(f"Failed to crawl related issue {related_issue_no}: {e}")
                            continue

        except Exception as e:
            logger.error(f"Failed to crawl issue {issue_id}: {e}")
            # Remove from crawled set since it failed (thread-safe)
            with self._crawled_lock:
                crawled_issue_ids.discard(issue_id)
            raise
        finally:
            # Cleanup browser resources
            page.close()
            browser.close()
            playwright.stop()

        return result

    def _crawl_issue_detail_with_page(self, page: Page, issue_url: str) -> Dict[str, Any]:
        """
        Crawl single issue detail page using provided page object
        (Used for parallel crawling where each thread has its own page)

        Args:
            page: Playwright page object to use
            issue_url: URL of the issue detail page

        Returns:
            Dictionary containing issue data
        """
        try:
            # Navigate to issue page
            page.goto(issue_url)
            page.wait_for_load_state('networkidle')

            # Expand hidden sections by clicking their toggle buttons
            self._expand_hidden_sections_with_page(page)

            # Parse issue page
            issue_data = self.parser.parse_issue_page(page)

            # Add metadata
            issue_data['url'] = issue_url
            issue_data['crawled_at'] = datetime.now().isoformat()

            # Download and process attachments
            if issue_data.get('attachments'):
                self.attachment_processor.process_attachments(
                    issue_data['attachments'],
                    page,
                    issue_data.get('issue_id', 'unknown')
                )

            return issue_data

        except Exception as e:
            logger.error(f"Failed to crawl issue detail {issue_url}: {e}")
            raise

    def _expand_hidden_sections_with_page(self, page: Page) -> None:
        """
        Expand hidden sections on the issue detail page by clicking toggle buttons
        (Used for parallel crawling where each thread has its own page)

        Args:
            page: Playwright page object to use

        Sections to expand:
        - NoticeDiv: Product notice (hidden by default)
        - IssueDescriptionDiv: Issue description (hidden by default)
        - PatchAttachesDiv: Patch files (hidden by default)
        - HistoriesDiv: Modification history (hidden by default)
        """
        try:
            import time

            # List of sections that are hidden by default and need to be clicked
            sections_to_expand = [
                ('NoticeDiv', 'Product Notice'),
                ('IssueDescriptionDiv', 'Issue Description'),
                ('PatchAttachesDiv', 'Patch Files'),
                ('HistoriesDiv', 'Modification History')
            ]

            for div_id, section_name in sections_to_expand:
                try:
                    # Find the toggle button using the onclick attribute
                    # Pattern: <td class="title6" onclick="setDisplay3(this, 'IssueDescriptionDiv');">
                    toggle_selector = f'td.title6[onclick*="{div_id}"]'
                    toggle_button = page.query_selector(toggle_selector)

                    if toggle_button:
                        # Check if section is currently hidden
                        section_div = page.query_selector(f'#{div_id}')
                        if section_div:
                            display_style = section_div.evaluate('el => getComputedStyle(el).display')

                            if display_style == 'none':
                                # Click to expand
                                toggle_button.click()
                                time.sleep(0.5)  # Wait for animation
                                logger.debug(f"Expanded section: {section_name}")
                            else:
                                logger.debug(f"Section already visible: {section_name}")
                        else:
                            logger.debug(f"Section not found: {section_name}")
                    else:
                        logger.debug(f"Toggle button not found for: {section_name}")

                except Exception as e:
                    logger.warning(f"Failed to expand {section_name}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error expanding hidden sections: {e}")

    def _execute_search(self, query: str, max_results: int, product: str = "") -> List[str]:
        """
        Execute search and extract issue URLs

        Args:
            query: Search query string
            max_results: Maximum number of results to retrieve
            product: Product filter for UI selection

        Returns:
            List of issue URLs
        """
        # TODO: Implement actual search execution based on IMS UI structure
        # This is a template that needs to be customized

        issue_links = []

        try:
            # Navigate to search page explicitly
            # (base URL might redirect to main page after auth)
            search_page_url = "https://ims.tmaxsoft.com/tody/ims/issue/issueSearchList.do?searchType=1&menuCode=issue_search"
            logger.info(f"Navigating to search page: {search_page_url}")
            self.page.goto(search_page_url)
            self.page.wait_for_load_state('networkidle')

            # Debug: Check current URL after navigation
            current_url = self.page.url
            logger.info(f"Current URL after navigation: {current_url}")

            # Wait for keyword input to be visible (increased timeout)
            try:
                self.page.wait_for_selector('#keyword', state='visible', timeout=15000)
            except Exception as e:
                # Debug: Take screenshot and dump HTML on failure
                screenshot_path = self.output_dir / f"debug_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.page.screenshot(path=str(screenshot_path))
                logger.error(f"Screenshot saved to: {screenshot_path}")
                logger.error(f"Page title: {self.page.title()}")
                logger.error(f"Current URL: {self.page.url}")
                raise

            # Select products: OpenFrame*, ProSort, Tibero
            logger.info(f"Selecting products for: {product}")

            # Get all product options
            product_select = self.page.query_selector('#productCodes')
            if product_select:
                # Deselect all first
                self.page.evaluate("""
                    document.getElementById('productCodes').selectedIndex = -1;
                    Array.from(document.getElementById('productCodes').options).forEach(opt => opt.selected = false);
                """)

                # Select products based on product parameter
                if product.lower() == 'openframe':
                    # Select all OpenFrame products
                    self.page.evaluate("""
                        Array.from(document.getElementById('productCodes').options)
                            .filter(opt => opt.text.startsWith('OpenFrame'))
                            .forEach(opt => opt.selected = true);
                    """)
                    logger.info("Selected all OpenFrame products")
                elif product.lower() == 'tibero':
                    # Select Tibero
                    self.page.select_option('#productCodes', value='070')
                    logger.info("Selected Tibero")
                elif product.lower() == 'prosort':
                    # Select ProSort
                    self.page.select_option('#productCodes', value='640')
                    logger.info("Selected ProSort")
                else:
                    # Default: Select OpenFrame, ProSort, ProTrieve
                    self.page.evaluate("""
                        Array.from(document.getElementById('productCodes').options)
                            .filter(opt =>
                                opt.text.startsWith('OpenFrame') ||
                                opt.value === '640' ||  // ProSort
                                opt.value === '425'     // ProTrieve
                            )
                            .forEach(opt => opt.selected = true);
                    """)
                    logger.info("Selected OpenFrame*, ProSort, ProTrieve products")

                # Trigger the onchange event
                self.page.evaluate("setProductCondition(document.getElementById('productCodes').value, 'ims', 'yijae.shin', 'issueSearch');")

            # Select all status/activities (including Closed issues)
            # This ensures we search across all issue states: New, Open, Assigned, Resolved, Closed, etc.
            activities_select = self.page.query_selector('#activities')
            if activities_select:
                logger.info("Selecting all issue statuses (including Closed)")
                # Select all available statuses
                self.page.evaluate("""
                    Array.from(document.getElementById('activities').options)
                        .forEach(opt => opt.selected = true);
                """)
                logger.info("Selected all issue statuses")

            # Clear any existing search first
            self.page.fill('#keyword', '')

            # Enter search query
            # TmaxSoft IMS: input#keyword
            self.page.fill('#keyword', query)

            # Submit search - call JS and wait generously for slow navigation
            logger.info("Submitting search...")

            # Call search function (don't wait for events, just call it)
            self.page.evaluate("goReportSearch(document.issueSearchForm, '1')")
            logger.info("Search function called")

            # Wait for URL to change (indicates navigation started)
            logger.info("Waiting for URL to change...")
            url_changed = False
            for i in range(60):  # Wait up to 60 seconds
                self.page.wait_for_timeout(1000)
                current_url = self.page.url
                if 'reSearchYN=Y' in current_url:
                    logger.info(f"URL changed after {i+1}s: {current_url}")
                    url_changed = True
                    break

            if not url_changed:
                logger.warning(f"URL did not change after 60s: {self.page.url}")

            # Wait for page to fully settle
            logger.info("Waiting for page to load completely...")
            try:
                self.page.wait_for_load_state('networkidle', timeout=30000)
            except PlaywrightTimeout:
                logger.warning("networkidle timeout, continuing anyway...")

            # Wait generously for results to appear
            logger.info("Waiting for result rows to appear...")
            try:
                self.page.wait_for_selector('tr.rowClickData', state='attached', timeout=30000)
                logger.info("Result rows found (attached to DOM)")

                # Now wait for them to be visible
                self.page.wait_for_selector('tr.rowClickData', state='visible', timeout=10000)
                result_rows = self.page.query_selector_all('tr.rowClickData')
                logger.info(f"Found {len(result_rows)} visible result rows")
            except PlaywrightTimeout as e:
                logger.error(f"No results found: {e}")
                # Take screenshot
                screenshot_path = self.output_dir / f"no_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.page.screenshot(path=str(screenshot_path))
                logger.info(f"Screenshot saved to: {screenshot_path}")

                # Also save HTML for debugging
                html_path = self.output_dir / f"no_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                html_content = self.page.content()
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"HTML saved to: {html_path}")

                raise PlaywrightTimeout(f"No search results found. URL: {self.page.url}")

            # Extract issue links from search results
            # TmaxSoft IMS: Results are in table rows with onclick handlers
            # <tr class="rowClickData" onclick="javascript:popBlankIssueView('348115', 'issue_search');">
            result_rows = self.page.query_selector_all('tr.rowClickData')

            logger.info(f"Found {len(result_rows)} result rows")

            for row in result_rows[:max_results]:
                onclick = row.get_attribute('onclick')
                if onclick:
                    # Extract issue ID from onclick="javascript:popBlankIssueView('348115', 'issue_search');"
                    import re
                    match = re.search(r"popBlankIssueView\('(\d+)'", onclick)
                    if match:
                        issue_id = match.group(1)
                        # Build direct URL to issue detail page (use issueView.do, not issueDetail.do!)
                        issue_url = f"https://ims.tmaxsoft.com/tody/ims/issue/issueView.do?issueId={issue_id}&menuCode=issue_search"
                        issue_links.append(issue_url)
                        logger.debug(f"Extracted issue ID: {issue_id}")

            # Handle pagination if needed
            # TODO: Implement pagination logic if results span multiple pages

        except PlaywrightTimeout as e:
            logger.error(f"Search timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            raise

        return issue_links

    def _expand_hidden_sections(self) -> None:
        """
        Expand hidden sections on the issue detail page by clicking toggle buttons

        Sections to expand:
        - IssueDescriptionDiv: Issue description (hidden by default)
        - PatchAttachesDiv: Patch files (hidden by default)
        - HistoriesDiv: Modification history (hidden by default)
        """
        try:
            import time

            # List of sections that are hidden by default and need to be clicked
            sections_to_expand = [
                ('NoticeDiv', 'Product Notice'),
                ('IssueDescriptionDiv', 'Issue Description'),
                ('PatchAttachesDiv', 'Patch Files'),
                ('HistoriesDiv', 'Modification History')
            ]

            for div_id, section_name in sections_to_expand:
                try:
                    # Find the toggle button using the onclick attribute
                    # Pattern: <td class="title6" onclick="setDisplay3(this, 'IssueDescriptionDiv');">
                    toggle_selector = f'td.title6[onclick*="{div_id}"]'
                    toggle_button = self.page.query_selector(toggle_selector)

                    if toggle_button:
                        # Check if section is currently hidden
                        section_div = self.page.query_selector(f'#{div_id}')
                        if section_div:
                            display_style = section_div.evaluate('el => getComputedStyle(el).display')

                            if display_style == 'none':
                                # Click to expand
                                toggle_button.click()
                                time.sleep(0.5)  # Wait for animation
                                logger.debug(f"Expanded section: {section_name}")
                            else:
                                logger.debug(f"Section already visible: {section_name}")
                        else:
                            logger.debug(f"Section not found: {section_name}")
                    else:
                        logger.debug(f"Toggle button not found for: {section_name}")

                except Exception as e:
                    logger.warning(f"Failed to expand {section_name}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error expanding hidden sections: {e}")

    def _crawl_issue_detail(self, issue_url: str) -> Dict[str, Any]:
        """
        Crawl single issue detail page

        Args:
            issue_url: URL of the issue detail page

        Returns:
            Dictionary containing issue data
        """
        try:
            # Navigate to issue page
            self.page.goto(issue_url)
            self.page.wait_for_load_state('networkidle')

            # Expand hidden sections by clicking their toggle buttons
            self._expand_hidden_sections()

            # Parse issue page
            issue_data = self.parser.parse_issue_page(self.page)

            # Add metadata
            issue_data['url'] = issue_url
            issue_data['crawled_at'] = datetime.now().isoformat()

            # Download and process attachments
            if issue_data.get('attachments'):
                self.attachment_processor.process_attachments(
                    issue_data['attachments'],
                    self.page,
                    issue_data.get('issue_id', 'unknown')
                )

            return issue_data

        except Exception as e:
            logger.error(f"Failed to crawl issue detail {issue_url}: {e}")
            raise

    def _save_issue(
        self,
        issue_data: Dict[str, Any],
        crawl_order: Optional[int] = None,
        crawl_duration_ms: Optional[int] = None
    ) -> None:
        """
        Save issue data to JSON file and database

        Args:
            issue_data: Issue data dictionary
            crawl_order: Order in which issue was crawled (for database)
            crawl_duration_ms: Time taken to crawl issue in milliseconds (for database)
        """
        try:
            issue_id = issue_data.get('issue_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{issue_id}_{timestamp}.json"
            filepath = self.output_dir / filename

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(issue_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved issue to {filepath}")

            # Track timing for statistics
            if crawl_duration_ms:
                with self._crawled_lock:
                    self._issue_times.append(crawl_duration_ms)

            # Save to database
            if self.db_saver:
                try:
                    self.db_saver.save_issue(
                        issue_data=issue_data,
                        crawl_order=crawl_order,
                        crawl_duration_ms=crawl_duration_ms
                    )
                    logger.debug(f"Saved issue {issue_id} to database")
                except Exception as e:
                    logger.error(f"Failed to save issue {issue_id} to database: {e}")
                    # Continue even if database save fails

        except Exception as e:
            logger.error(f"Failed to save issue {issue_data.get('issue_id')}: {e}")
