"""
IMS Page Parser
Extracts structured data from TmaxSoft IMS issue pages
"""
import logging
import re
from typing import Dict, Any, List, Optional
from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class IMSParser:
    """Parses TmaxSoft IMS issue pages and extracts structured data"""

    def parse_issue_page(self, page: Page) -> Dict[str, Any]:
        """
        Parse issue detail page and extract all relevant data

        Args:
            page: Playwright Page object on issue detail page

        Returns:
            Dictionary containing structured issue data
        """
        try:
            issue_data = {
                'issue_id': self._extract_issue_id(page),
                'title': self._extract_title(page),
                'description': self._extract_description(page),
                'product': self._extract_product(page),
                'status': self._extract_status(page),
                'priority': self._extract_priority(page),
                'created_date': self._extract_created_date(page),
                'updated_date': self._extract_updated_date(page),
                'reporter': self._extract_reporter(page),
                'assignee': self._extract_assignee(page),
                'product_notice': self._extract_product_notice(page),
                'related_issues': self._extract_related_issues(page),
                'comments': self._extract_comments(page),
                'history': self._extract_history(page),
                'attachments': self._extract_attachments(page),
                'metadata': self._extract_metadata(page)
            }

            logger.debug(f"Parsed issue: {issue_data['issue_id']}")
            return issue_data

        except Exception as e:
            logger.error(f"Failed to parse issue page: {e}")
            raise

    def _extract_issue_id(self, page: Page) -> str:
        """Extract issue ID from span.issueNumber"""
        try:
            # TmaxSoft IMS uses: <span class="issueNumber">348115</span>
            element = page.query_selector('span.issueNumber')
            if element:
                return element.text_content().strip()

            # Fallback: extract from URL
            url = page.url
            # URL pattern: ...issueView.do?issueId=350334
            if 'issueId=' in url:
                match = re.search(r'issueId=(\d+)', url)
                if match:
                    return match.group(1)

            return 'unknown'
        except Exception as e:
            logger.warning(f"Failed to extract issue ID: {e}")
            return 'unknown'

    def _extract_title(self, page: Page) -> str:
        """Extract issue title/subject from table row"""
        try:
            # Find the table row with "Subject" header in the main content area
            # Pattern: <td class="tableHeaderTitle">Subject</td><td>...</td>
            # The issue title is in a table with class="table-bordered dataTable fullWidth"

            # Strategy: Find the specific table that contains issue metadata
            # This table has the tableHeaderTitle structure and is NOT in navigation
            metadata_tables = page.query_selector_all('table.table-bordered.dataTable.fullWidth')

            for table in metadata_tables:
                rows = table.query_selector_all('tr')
                for row in rows:
                    header = row.query_selector('td.tableHeaderTitle')
                    if header and 'Subject' == header.text_content().strip():
                        # Get all td elements, the second one is the data cell
                        cells = row.query_selector_all('td')
                        if len(cells) >= 2:
                            title = cells[1].text_content().strip()
                            # Clean up whitespace
                            title = re.sub(r'\s+', ' ', title)

                            # Skip if empty or only whitespace
                            if not title:
                                continue

                            return title

            return ''
        except Exception as e:
            logger.warning(f"Failed to extract title: {e}")
            return ''

    def _extract_description(self, page: Page) -> str:
        """Extract issue description from IssueDescriptionDiv"""
        try:
            # TmaxSoft IMS: <div id="IssueDescriptionDiv"> ... <td class="data">
            desc_div = page.query_selector('#IssueDescriptionDiv')
            if desc_div:
                # Get the content cell
                data_cell = desc_div.query_selector('td.data')
                if data_cell:
                    # Get text content
                    text_content = data_cell.text_content().strip()

                    # Remove "Issue Description" header if present
                    # Pattern: "Issue Description\n\n\n   actual content..."
                    if text_content.startswith('Issue Description'):
                        # Find where the actual content starts (after the header)
                        lines = text_content.split('\n')
                        # Skip "Issue Description" and empty lines
                        actual_content_lines = []
                        skip_header = True
                        for line in lines:
                            stripped = line.strip()
                            if skip_header:
                                if stripped == 'Issue Description' or stripped == '':
                                    continue
                                else:
                                    skip_header = False
                            if not skip_header:
                                actual_content_lines.append(line)
                        text_content = '\n'.join(actual_content_lines).strip()

                    return text_content
            return ''
        except Exception as e:
            logger.warning(f"Failed to extract description: {e}")
            return ''

    def _extract_field_by_header(self, page: Page, header_text: str) -> str:
        """
        Generic method to extract field value by header text
        Pattern: <td class="title tableHeaderTitle">Header</td><td class="data">Value</td>
        """
        try:
            rows = page.query_selector_all('tr')
            for row in rows:
                header = row.query_selector('td.title.tableHeaderTitle')
                if header and header_text in header.text_content():
                    data_cell = row.query_selector('td.data')
                    if data_cell:
                        return data_cell.text_content().strip()
            return ''
        except Exception as e:
            logger.warning(f"Failed to extract field '{header_text}': {e}")
            return ''

    def _extract_product(self, page: Page) -> str:
        """Extract product name"""
        return self._extract_field_by_header(page, 'Product')

    def _extract_status(self, page: Page) -> str:
        """Extract issue status"""
        try:
            # Status might have colored span inside
            rows = page.query_selector_all('tr')
            for row in rows:
                header = row.query_selector('td.title.tableHeaderTitle')
                if header and 'Status' in header.text_content():
                    data_cell = row.query_selector('td.data')
                    if data_cell:
                        # Try to get span content first (colored status)
                        span = data_cell.query_selector('span')
                        if span:
                            return span.text_content().strip()
                        return data_cell.text_content().strip()
            return ''
        except Exception as e:
            logger.warning(f"Failed to extract status: {e}")
            return ''

    def _extract_priority(self, page: Page) -> str:
        """Extract issue priority"""
        return self._extract_field_by_header(page, 'Priority')

    def _extract_created_date(self, page: Page) -> str:
        """Extract creation date (Registered date)"""
        return self._extract_field_by_header(page, 'Registered date')

    def _extract_updated_date(self, page: Page) -> str:
        """Extract last updated date (Date of final order or Closed Date)"""
        # Try "Date of final order" first
        date = self._extract_field_by_header(page, 'Date of final order')
        if not date:
            # Try "Closed Date" if issue is closed
            date = self._extract_field_by_header(page, 'Closed Date')
        return date

    def _extract_reporter(self, page: Page) -> str:
        """Extract reporter name and email"""
        return self._extract_field_by_header(page, 'Reporter')

    def _extract_assignee(self, page: Page) -> str:
        """Extract Handler (assignee) name and email"""
        return self._extract_field_by_header(page, 'Handler')

    def _extract_comments(self, page: Page) -> List[Dict[str, Any]]:
        """Extract comments/actions from CommentsDiv"""
        comments = []
        try:
            # TmaxSoft IMS: <div id="CommentsDiv"> contains <div class="fieldset"> for each comment
            comments_div = page.query_selector('#CommentsDiv')
            if not comments_div:
                return comments

            fieldsets = comments_div.query_selector_all('div.fieldset')

            for fieldset in fieldsets:
                try:
                    # Extract action info from legend
                    legend = fieldset.query_selector('div.legend')
                    if not legend:
                        continue

                    # Action No and metadata from span
                    # Pattern: " Action No.   2258642   |   Registrant : 민사혁   |   Registered date ..."
                    action_span = legend.query_selector('span.link2[id^="action_"]')
                    if not action_span:
                        continue

                    action_text = action_span.text_content()

                    # Parse action metadata
                    action_no = ''
                    author = ''
                    date = ''

                    # Extract Action No
                    action_match = re.search(r'Action No\.\s+(\d+)', action_text)
                    if action_match:
                        action_no = action_match.group(1)

                    # Extract Registrant
                    registrant_match = re.search(r'Registrant\s*:\s*([^|]+)', action_text)
                    if registrant_match:
                        author = registrant_match.group(1).strip()

                    # Extract Registered date
                    date_match = re.search(r'Registered date\s*:\s*([^\|]+)', action_text)
                    if date_match:
                        date = date_match.group(1).strip()

                    # Extract comment content
                    # Pattern: <div id="comment_2258642"> ... <div class="commDescTR data">
                    action_id = action_span.get_attribute('id').replace('action_', '')
                    comment_div = fieldset.query_selector(f'div#comment_{action_id}')
                    content = ''
                    if comment_div:
                        desc_div = comment_div.query_selector('div.commDescTR')
                        if desc_div:
                            content = desc_div.text_content().strip()

                    comment = {
                        'action_no': action_no,
                        'author': author,
                        'date': date,
                        'content': content
                    }
                    comments.append(comment)

                except Exception as e:
                    logger.warning(f"Failed to parse comment: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract comments: {e}")

        return comments

    def _extract_history(self, page: Page) -> List[Dict[str, Any]]:
        """Extract change history from HistoriesDiv"""
        history = []
        try:
            # TmaxSoft IMS: <div id="HistoriesDiv"> contains table with rows
            history_div = page.query_selector('#HistoriesDiv')
            if not history_div:
                return history

            # Get all data rows (skip header)
            rows = history_div.query_selector_all('tr.data')

            for row in rows:
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) >= 3:
                        history_entry = {
                            'date': cells[0].text_content().strip(),
                            'user': cells[1].text_content().strip(),
                            'details': cells[2].text_content().strip()
                        }
                        history.append(history_entry)
                except Exception as e:
                    logger.warning(f"Failed to parse history entry: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract history: {e}")

        return history

    def _extract_attachments(self, page: Page) -> List[Dict[str, Any]]:
        """Extract attachment information from AttachesDiv and PatchAttachesDiv"""
        attachments = []
        try:
            # Regular attachments
            attachments.extend(self._extract_attachments_from_div(page, '#AttachesDiv', 'regular'))

            # Patch files
            attachments.extend(self._extract_attachments_from_div(page, '#PatchAttachesDiv', 'patch'))

        except Exception as e:
            logger.warning(f"Failed to extract attachments: {e}")

        return attachments

    def _extract_attachments_from_div(self, page: Page, div_selector: str, file_type: str) -> List[Dict[str, Any]]:
        """Helper to extract attachments from a specific div"""
        attachments = []
        try:
            div = page.query_selector(div_selector)
            if not div:
                return attachments

            # Find all download links
            # Pattern: <a href="/" onclick="downloadFileNew('261102', 'ISSUE')">
            links = div.query_selector_all('a[onclick^="downloadFileNew"]')

            for link in links:
                try:
                    # Extract file ID from onclick
                    onclick = link.get_attribute('onclick') or ''
                    file_id_match = re.search(r"downloadFileNew\('(\d+)'", onclick)
                    file_id = file_id_match.group(1) if file_id_match else ''

                    # Get filename from span inside link
                    filename_span = link.query_selector('span')
                    filename = filename_span.text_content().strip() if filename_span else ''

                    # Get file size - usually in a span after the link
                    size = ''
                    # Try to find size in next sibling or parent's text
                    parent = link.evaluate_handle('node => node.parentElement')
                    if parent:
                        parent_text = parent.as_element().text_content() if parent.as_element() else ''
                        size_match = re.search(r'\(([^)]+)\)', parent_text)
                        if size_match:
                            size = size_match.group(1)

                    if filename:
                        attachment = {
                            'name': filename,
                            'file_id': file_id,
                            'size': size,
                            'type': file_type
                        }
                        attachments.append(attachment)

                except Exception as e:
                    logger.warning(f"Failed to parse attachment: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract attachments from {div_selector}: {e}")

        return attachments

    def _extract_product_notice(self, page: Page) -> str:
        """Extract product notice from NoticeDiv"""
        try:
            # TmaxSoft IMS: <div id="NoticeDiv"> contains product notice content
            notice_div = page.query_selector('#NoticeDiv')
            if not notice_div:
                return ''

            # Get all text content from the notice div
            # Skip the Subject header row, get actual notice content
            tables = notice_div.query_selector_all('table')
            if tables:
                # Usually the notice content is in the first table
                for table in tables:
                    rows = table.query_selector_all('tr')
                    for row in rows:
                        # Skip the header row with "Subject"
                        header = row.query_selector('td.tableHeaderTitle')
                        if header and 'Subject' in header.text_content():
                            continue

                        # Get the content
                        cells = row.query_selector_all('td')
                        if cells:
                            # Get text from all cells
                            content_parts = []
                            for cell in cells:
                                text = cell.text_content().strip()
                                if text and text != 'Subject':
                                    content_parts.append(text)
                            if content_parts:
                                return '\n'.join(content_parts)

            # Fallback: get all text content
            return notice_div.text_content().strip()

        except Exception as e:
            logger.warning(f"Failed to extract product notice: {e}")
            return ''

    def _extract_related_issues(self, page: Page) -> List[Dict[str, Any]]:
        """Extract related issues from RelatedIssueTable"""
        related_issues = []
        try:
            # TmaxSoft IMS: <table id="RelatedIssueTable">
            table = page.query_selector('#RelatedIssueTable')
            if not table:
                return related_issues

            # Get data rows (skip header)
            tbody = table.query_selector('tbody')
            if tbody:
                rows = tbody.query_selector_all('tr')
            else:
                rows = table.query_selector_all('tr')

            # Skip header row
            for row in rows:
                # Check if this is a header row
                if row.query_selector('th'):
                    continue

                try:
                    cells = row.query_selector_all('td')
                    if len(cells) >= 8:  # Expected: No, Issue No, Status, Product, Module, Owner, Handler, Customer, Project, Subject
                        # Parse related issue data
                        issue_no_cell = cells[1]  # Issue No column
                        issue_link = issue_no_cell.query_selector('a')
                        if issue_link:
                            issue_no = issue_link.text_content().strip()
                        else:
                            issue_no = issue_no_cell.text_content().strip()

                        related_issue = {
                            'issue_no': issue_no,
                            'status': cells[2].text_content().strip() if len(cells) > 2 else '',
                            'product': cells[3].text_content().strip() if len(cells) > 3 else '',
                            'module': cells[4].text_content().strip() if len(cells) > 4 else '',
                            'owner': cells[5].text_content().strip() if len(cells) > 5 else '',
                            'handler': cells[6].text_content().strip() if len(cells) > 6 else '',
                            'customer': cells[7].text_content().strip() if len(cells) > 7 else '',
                        }

                        # Add project and subject if available
                        if len(cells) > 8:
                            related_issue['project'] = cells[8].text_content().strip()
                        if len(cells) > 9:
                            related_issue['subject'] = cells[9].text_content().strip()

                        if issue_no:  # Only add if we have an issue number
                            related_issues.append(related_issue)

                except Exception as e:
                    logger.warning(f"Failed to parse related issue row: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract related issues: {e}")

        return related_issues

    def _extract_metadata(self, page: Page) -> Dict[str, Any]:
        """Extract additional metadata fields"""
        metadata = {}
        try:
            # Extract additional IMS-specific fields
            fields_to_extract = [
                'Category',
                'Version',
                'Build No',
                'Patch No',
                'Module',
                'Error Code',
                'Severity',
                'Project',
                'Customer',
                'Owner',
                'Patch Version',
                'Bug Number'
            ]

            for field in fields_to_extract:
                value = self._extract_field_by_header(page, field)
                if value:
                    # Convert field name to snake_case key
                    key = field.lower().replace(' ', '_')
                    metadata[key] = value

        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")

        return metadata

    @staticmethod
    def _get_text(parent_element, selector: str) -> str:
        """
        Helper method to safely extract text from element

        Args:
            parent_element: Parent Playwright element
            selector: CSS selector for target element

        Returns:
            Extracted text or empty string
        """
        try:
            element = parent_element.query_selector(selector)
            return element.text_content().strip() if element else ''
        except Exception:
            return ''
