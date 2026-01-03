"""
Utility functions for IMS Crawler
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List


def create_crawl_folder_name(product: str, keywords: str, timestamp: Optional[datetime] = None) -> str:
    """
    Create folder name for crawl session

    Format: {product}_{sanitized_keywords}_{timestamp}
    Example: OpenFrame_TPETIME_error_20260103_154530

    Args:
        product: Product name
        keywords: Search keywords
        timestamp: Optional timestamp (default: now)

    Returns:
        Folder name string
    """
    if timestamp is None:
        timestamp = datetime.now()

    # Sanitize product name
    safe_product = re.sub(r'[^\w\-]', '_', product)

    # Sanitize keywords (remove special chars, limit length)
    # Remove IMS operators (+, ', ")
    clean_keywords = re.sub(r'[+\'"]', '', keywords)
    # Replace spaces and special chars with underscore
    safe_keywords = re.sub(r'[^\w\-가-힣ぁ-んァ-ヶ一-龯]', '_', clean_keywords)
    # Remove consecutive underscores
    safe_keywords = re.sub(r'_+', '_', safe_keywords)
    # Limit length
    safe_keywords = safe_keywords[:50]
    # Remove trailing underscore
    safe_keywords = safe_keywords.strip('_')

    # Format timestamp
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S")

    # Combine
    folder_name = f"{safe_product}_{safe_keywords}_{ts_str}"

    return folder_name


def get_latest_crawl_folder(base_dir: Path, product: Optional[str] = None) -> Optional[Path]:
    """
    Get the most recent crawl folder

    Args:
        base_dir: Base directory containing crawl folders
        product: Optional product filter

    Returns:
        Path to latest folder or None if no folders found
    """
    if not base_dir.exists():
        return None

    # List all subdirectories
    folders = [f for f in base_dir.iterdir() if f.is_dir()]

    # Filter by product if specified
    if product:
        folders = [f for f in folders if f.name.startswith(f"{product}_")]

    if not folders:
        return None

    # Sort by modification time (most recent first)
    folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    return folders[0]


def list_crawl_folders(base_dir: Path, product: Optional[str] = None, limit: int = 10) -> List[Path]:
    """
    List crawl folders sorted by timestamp (newest first)

    Args:
        base_dir: Base directory containing crawl folders
        product: Optional product filter
        limit: Maximum number of folders to return

    Returns:
        List of folder paths
    """
    if not base_dir.exists():
        return []

    # List all subdirectories
    folders = [f for f in base_dir.iterdir() if f.is_dir()]

    # Filter by product if specified
    if product:
        folders = [f for f in folders if f.name.startswith(f"{product}_")]

    # Sort by modification time (most recent first)
    folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    return folders[:limit]


def parse_folder_metadata(folder_name: str) -> dict:
    """
    Parse metadata from folder name

    Args:
        folder_name: Folder name (e.g., "OpenFrame_TPETIME_20260103_154530")

    Returns:
        Dictionary with product, keywords, timestamp
    """
    parts = folder_name.split('_')

    if len(parts) < 3:
        return {
            'product': 'Unknown',
            'keywords': folder_name,
            'timestamp': None
        }

    # Last 2 parts are timestamp (YYYYMMDD_HHMMSS)
    ts_date = parts[-2] if len(parts) >= 2 else ''
    ts_time = parts[-1] if len(parts) >= 1 else ''

    # Try to parse timestamp
    timestamp = None
    try:
        timestamp_str = f"{ts_date}_{ts_time}"
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
    except:
        pass

    # Product is first part
    product = parts[0]

    # Keywords are middle parts
    if timestamp:
        keywords = '_'.join(parts[1:-2]) if len(parts) > 3 else ''
    else:
        keywords = '_'.join(parts[1:])

    return {
        'product': product,
        'keywords': keywords,
        'timestamp': timestamp
    }
