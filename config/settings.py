"""
Configuration management for IMS Crawler
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# IMS Configuration
IMS_BASE_URL = os.getenv("IMS_BASE_URL", "")
IMS_USERNAME = os.getenv("IMS_USERNAME", "")
IMS_PASSWORD = os.getenv("IMS_PASSWORD", "")

# Crawler Settings
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
DEFAULT_MAX_RESULTS = int(os.getenv("DEFAULT_MAX_RESULTS", "100"))
DOWNLOAD_ATTACHMENTS = os.getenv("DOWNLOAD_ATTACHMENTS", "true").lower() == "true"

# Session Management
SESSION_TIMEOUT_MINUTES = 30
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

# Output Settings
OUTPUT_DIR = PROJECT_ROOT / os.getenv("OUTPUT_DIR", "data/issues")
ATTACHMENTS_DIR = PROJECT_ROOT / os.getenv("ATTACHMENTS_DIR", "data/attachments")

# Create directories if they don't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Playwright Settings
HEADLESS = True
BROWSER_TIMEOUT = 30000  # milliseconds

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
