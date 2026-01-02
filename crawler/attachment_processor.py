"""
Attachment Processor
Downloads and extracts text from various file types
"""
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from playwright.sync_api import Page
import PyPDF2
import pdfplumber
from docx import Document
from PIL import Image

logger = logging.getLogger(__name__)


class AttachmentProcessor:
    """Processes and downloads issue attachments"""

    def __init__(self, attachments_dir: Path):
        self.attachments_dir = attachments_dir
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

    def process_attachments(
        self,
        attachments: List[Dict[str, Any]],
        page: Page,
        issue_id: str
    ) -> None:
        """
        Process all attachments for an issue

        Args:
            attachments: List of attachment metadata dicts
            page: Playwright Page object (for downloading)
            issue_id: Issue ID for organizing files
        """
        issue_dir = self.attachments_dir / self._sanitize_filename(issue_id)
        issue_dir.mkdir(exist_ok=True)

        for attachment in attachments:
            try:
                self._download_attachment(attachment, page, issue_dir)
            except Exception as e:
                logger.error(f"Failed to process attachment {attachment.get('name')}: {e}")

    def _download_attachment(
        self,
        attachment: Dict[str, Any],
        page: Page,
        target_dir: Path
    ) -> None:
        """
        Download single attachment

        Args:
            attachment: Attachment metadata dict
            page: Playwright Page object
            target_dir: Directory to save file
        """
        try:
            url = attachment.get('url')
            filename = self._sanitize_filename(attachment.get('name', 'unknown'))

            if not url:
                logger.warning(f"No URL for attachment: {filename}")
                return

            # Make URL absolute if needed
            if not url.startswith('http'):
                base_url = page.url.split('/')[0:3]
                url = '/'.join(base_url) + url

            # Download file
            filepath = target_dir / filename

            # Use Playwright's download feature or direct request
            with page.expect_download() as download_info:
                page.goto(url)
                download = download_info.value

            download.save_as(filepath)
            logger.info(f"Downloaded: {filename}")

            # Extract text if applicable
            extracted_text = self._extract_text(filepath)
            if extracted_text:
                # Save extracted text alongside file
                text_filepath = filepath.with_suffix(filepath.suffix + '.txt')
                with open(text_filepath, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                logger.debug(f"Extracted text from {filename}")

                # Update attachment metadata
                attachment['local_path'] = str(filepath)
                attachment['extracted_text'] = extracted_text[:1000]  # Store preview

        except Exception as e:
            logger.error(f"Download failed for {attachment.get('name')}: {e}")

    def _extract_text(self, filepath: Path) -> str:
        """
        Extract text content from file

        Args:
            filepath: Path to file

        Returns:
            Extracted text or empty string
        """
        suffix = filepath.suffix.lower()

        try:
            if suffix == '.txt' or suffix == '.log':
                return self._extract_from_text(filepath)
            elif suffix == '.pdf':
                return self._extract_from_pdf(filepath)
            elif suffix in ['.doc', '.docx']:
                return self._extract_from_docx(filepath)
            elif suffix in ['.png', '.jpg', '.jpeg', '.bmp']:
                return self._extract_from_image(filepath)
            else:
                logger.debug(f"No text extraction for {suffix} files")
                return ''

        except Exception as e:
            logger.error(f"Text extraction failed for {filepath}: {e}")
            return ''

    @staticmethod
    def _extract_from_text(filepath: Path) -> str:
        """Extract text from plain text file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read text file {filepath}: {e}")
            return ''

    @staticmethod
    def _extract_from_pdf(filepath: Path) -> str:
        """Extract text from PDF file"""
        text_parts = []

        # Try pdfplumber first (better for complex PDFs)
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            if text_parts:
                return '\n\n'.join(text_parts)
        except Exception as e:
            logger.warning(f"pdfplumber failed for {filepath}: {e}")

        # Fallback to PyPDF2
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return '\n\n'.join(text_parts)
        except Exception as e:
            logger.error(f"PyPDF2 also failed for {filepath}: {e}")
            return ''

    @staticmethod
    def _extract_from_docx(filepath: Path) -> str:
        """Extract text from Word document"""
        try:
            doc = Document(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return '\n\n'.join(paragraphs)
        except Exception as e:
            logger.error(f"Failed to extract from DOCX {filepath}: {e}")
            return ''

    @staticmethod
    def _extract_from_image(filepath: Path) -> str:
        """
        Extract text from image using OCR
        Note: Requires pytesseract and Tesseract OCR installed
        """
        try:
            # Optional: OCR support
            # Requires: pip install pytesseract
            # And Tesseract OCR installed on system
            import pytesseract
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
            return text
        except ImportError:
            logger.debug("pytesseract not installed, skipping OCR")
            return ''
        except Exception as e:
            logger.error(f"OCR failed for {filepath}: {e}")
            return ''

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to be filesystem-safe

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Limit length
        if len(filename) > 255:
            # Keep extension
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 250 - len(ext)
            filename = name[:max_name_length] + '.' + ext if ext else name[:255]

        return filename
