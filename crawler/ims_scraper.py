"""
Main IMS Scraper Engine
Orchestrates the crawling process using Playwright
"""
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from .auth import AuthManager, AuthenticationError
from .search import SearchQueryBuilder
from .parser import IMSParser
from .attachment_processor import AttachmentProcessor

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
        headless: bool = True
    ):
        self.base_url = base_url
        self.output_dir = output_dir
        self.attachments_dir = attachments_dir
        self.headless = headless

        # Initialize components
        self.auth_manager = AuthManager(base_url, username, password)
        self.query_builder = SearchQueryBuilder()
        self.parser = IMSParser()
        self.attachment_processor = AttachmentProcessor(attachments_dir)

        # Browser and page objects (initialized in context manager)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def __enter__(self):
        """Context manager entry - initialize browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
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
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Main crawling method

        Args:
            product: Product name to filter by
            keywords: Search keywords (using IMS syntax)
            max_results: Maximum number of issues to crawl

        Returns:
            List of crawled issue data as dictionaries
        """
        if not self.page:
            raise RuntimeError("Scraper not initialized. Use context manager (with statement)")

        try:
            # Step 1: Authenticate
            logger.info("Step 1: Authenticating...")
            self.auth_manager.login(self.page)

            # Step 2: Build search query
            logger.info("Step 2: Building search query...")
            search_query = self.query_builder.build_query(keywords, product)
            logger.info(f"Search query: {search_query}")

            # Step 3: Execute search
            logger.info("Step 3: Executing search...")
            issue_links = self._execute_search(search_query, max_results)
            logger.info(f"Found {len(issue_links)} issues to crawl")

            # Step 4: Crawl each issue
            logger.info("Step 4: Crawling issues...")
            crawled_issues = []
            for idx, issue_url in enumerate(issue_links, 1):
                logger.info(f"Crawling issue {idx}/{len(issue_links)}: {issue_url}")

                try:
                    # Ensure session is still valid
                    self.auth_manager.ensure_authenticated(self.page)

                    # Crawl issue detail
                    issue_data = self._crawl_issue_detail(issue_url)
                    crawled_issues.append(issue_data)

                    # Save progress incrementally
                    self._save_issue(issue_data)

                except Exception as e:
                    logger.error(f"Failed to crawl issue {issue_url}: {e}")
                    continue

            logger.info(f"Successfully crawled {len(crawled_issues)} issues")
            return crawled_issues

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Crawling failed: {e}")
            raise

    def _execute_search(self, query: str, max_results: int) -> List[str]:
        """
        Execute search and extract issue URLs

        Args:
            query: Search query string
            max_results: Maximum number of results to retrieve

        Returns:
            List of issue URLs
        """
        # TODO: Implement actual search execution based on IMS UI structure
        # This is a template that needs to be customized

        issue_links = []

        try:
            # Navigate to search page
            # TODO: Update URL based on actual IMS search endpoint
            search_url = f"{self.base_url}/search"
            self.page.goto(search_url)

            # Enter search query
            # TODO: Update selector based on actual search input field
            self.page.fill('input[name="search"]', query)

            # Submit search
            # TODO: Update based on actual search button
            self.page.click('button[type="submit"]')

            # Wait for results
            self.page.wait_for_load_state('networkidle')

            # Extract issue links from search results
            # TODO: Update selector based on actual result list structure
            # This is a placeholder - needs customization
            result_elements = self.page.query_selector_all('.issue-link')

            for element in result_elements[:max_results]:
                href = element.get_attribute('href')
                if href:
                    # Convert relative URL to absolute if needed
                    if not href.startswith('http'):
                        href = f"{self.base_url}{href}"
                    issue_links.append(href)

            # Handle pagination if needed
            # TODO: Implement pagination logic if results span multiple pages

        except PlaywrightTimeout as e:
            logger.error(f"Search timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            raise

        return issue_links

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

    def _save_issue(self, issue_data: Dict[str, Any]) -> None:
        """
        Save issue data to JSON file

        Args:
            issue_data: Issue data dictionary
        """
        try:
            issue_id = issue_data.get('issue_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{issue_id}_{timestamp}.json"
            filepath = self.output_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(issue_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved issue to {filepath}")

        except Exception as e:
            logger.error(f"Failed to save issue {issue_data.get('issue_id')}: {e}")
