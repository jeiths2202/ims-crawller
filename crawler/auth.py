"""
Authentication Manager for IMS System
Handles login, session management, and timeout recovery
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page, BrowserContext, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AuthManager:
    """Manages authentication and session for IMS system"""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        session_timeout_minutes: int = 30,
        cookie_file: Optional[str] = None
    ):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.last_login_time = None
        self.is_authenticated = False
        self.cookie_file = cookie_file
        self.use_cookies = cookie_file and Path(cookie_file).exists()

    def login(self, page: Page, context: Optional[BrowserContext] = None) -> bool:
        """
        Perform login to IMS system with automatic fallback

        Args:
            page: Playwright Page object
            context: Playwright BrowserContext (needed for cookie-based auth)

        Returns:
            bool: True if login successful

        Raises:
            AuthenticationError: If all login methods fail
        """
        # Try cookie-based authentication first if available
        if self.use_cookies and context:
            try:
                logger.info("Attempting cookie-based authentication...")
                if self._login_with_cookies(page, context):
                    return True
            except AuthenticationError as e:
                logger.warning(f"Cookie authentication failed: {e}")
                logger.info("Falling back to form-based login with credentials from .env")

        # Fall back to form-based login
        try:
            logger.info(f"Attempting form-based login to {self.base_url}")

            # Navigate to login page
            page.goto(self.base_url)
            page.wait_for_load_state('networkidle')

            # Check if we're on login page
            current_url = page.url
            if 'login.do' not in current_url:
                # Already logged in or wrong page
                if self._verify_login_success(page):
                    logger.info("Already authenticated")
                    self.is_authenticated = True
                    self.last_login_time = datetime.now()
                    return True

            # Wait for login form to be visible
            page.wait_for_selector('input[name="id"]', state='visible', timeout=10000)

            # Fill login form (TmaxSoft IMS selectors)
            logger.info(f"Logging in as: {self.username}")
            page.fill('input[name="id"]', self.username)
            page.fill('input[name="password"]', self.password)

            # Submit form - look for login button (image type for TmaxSoft IMS)
            page.click('input[type="image"], button[type="submit"], input[type="submit"], button.btn-login')

            # Wait for navigation after login
            page.wait_for_load_state('networkidle')

            # Verify login success
            if self._verify_login_success(page):
                self.is_authenticated = True
                self.last_login_time = datetime.now()
                logger.info("Form-based login successful")
                return True
            else:
                raise AuthenticationError("Login verification failed - still on login page")

        except PlaywrightTimeout as e:
            logger.error(f"Login timeout: {e}")
            raise AuthenticationError(f"Login timeout: {e}")
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise AuthenticationError(f"Login failed: {e}")

    def _login_with_cookies(self, page: Page, context: BrowserContext) -> bool:
        """
        Login using saved browser cookies

        Args:
            page: Playwright Page object
            context: Playwright BrowserContext

        Returns:
            bool: True if login successful

        Raises:
            AuthenticationError: If cookie-based auth fails
        """
        try:
            logger.info(f"Loading cookies from {self.cookie_file}")

            # Load cookies from file
            cookies = self._load_cookies(self.cookie_file)

            # Add cookies to browser context
            context.add_cookies(cookies)
            logger.info(f"Added {len(cookies)} cookies to browser")

            # Navigate to IMS
            page.goto(self.base_url)
            page.wait_for_load_state('networkidle')

            # Verify we're logged in
            if self._verify_login_success(page):
                self.is_authenticated = True
                self.last_login_time = datetime.now()
                logger.info("Cookie-based authentication successful")
                return True
            else:
                logger.warning("Cookies loaded but verification failed")
                raise AuthenticationError("Cookie-based authentication failed - cookies may be expired")

        except Exception as e:
            logger.error(f"Cookie-based authentication failed: {e}")
            raise AuthenticationError(f"Cookie authentication failed: {e}")

    def _load_cookies(self, cookie_file: str) -> List[Dict[str, Any]]:
        """
        Load cookies from JSON file

        Args:
            cookie_file: Path to cookies JSON file

        Returns:
            List of cookie dictionaries
        """
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            return cookies
        except Exception as e:
            raise AuthenticationError(f"Failed to load cookies from {cookie_file}: {e}")

    def _verify_login_success(self, page: Page) -> bool:
        """
        Verify that login was successful by checking URL and page content

        Args:
            page: Playwright Page object

        Returns:
            bool: True if logged in, False if still on login page
        """
        try:
            current_url = page.url
            page_title = page.title()

            logger.debug(f"Verification - URL: {current_url}")
            logger.debug(f"Verification - Title: {page_title}")

            # Check if we're still on login page (negative check)
            if 'login.do' in current_url:
                logger.warning("Still on login page - authentication failed")
                return False

            # Check if redirected to login (authentication expired/failed)
            if '/auth/login' in current_url:
                logger.warning("Redirected to login page - authentication failed")
                return False

            # Check page title for login indicators
            if 'login' in page_title.lower():
                logger.warning(f"Page title contains 'login': {page_title}")
                return False

            # Positive checks - we're on IMS authenticated page
            if 'ims.tmaxsoft.com/tody/ims' in current_url:
                logger.info("Successfully authenticated - on IMS page")
                return True

            # If we reach here, we're not obviously on login page
            # Consider it successful
            logger.info("Authentication appears successful")
            return True

        except Exception as e:
            logger.error(f"Login verification error: {e}")
            return False

    def is_session_valid(self) -> bool:
        """
        Check if current session is still valid

        Returns:
            bool: True if session is valid
        """
        if not self.is_authenticated or self.last_login_time is None:
            return False

        elapsed_time = datetime.now() - self.last_login_time
        return elapsed_time < self.session_timeout

    def ensure_authenticated(self, page: Page) -> None:
        """
        Ensure user is authenticated, re-login if session expired

        Args:
            page: Playwright Page object

        Raises:
            AuthenticationError: If re-authentication fails
        """
        if not self.is_session_valid():
            logger.info("Session expired, re-authenticating...")
            self.login(page)

    def logout(self, page: Page) -> None:
        """
        Logout from IMS system

        Args:
            page: Playwright Page object
        """
        try:
            # TODO: Implement logout logic if needed
            logger.info("Logging out...")
            self.is_authenticated = False
            self.last_login_time = None
        except Exception as e:
            logger.warning(f"Logout error (non-critical): {e}")
