"""
Report Generator for IMS Issues
Analyzes crawled issue data and generates comprehensive markdown reports
Supports offline mode (template-based) and online mode (LLM-enhanced)
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Autonomous report generation engine"""

    def __init__(self, llm_client=None):
        """
        Initialize report generator

        Args:
            llm_client: Optional LLM client for enhanced analysis (Ollama, etc.)
        """
        self.llm_client = llm_client
        self.use_llm = llm_client is not None

    def load_issues(self, issue_dir: Path) -> List[Dict[str, Any]]:
        """
        Load all issue JSON files from directory

        Args:
            issue_dir: Directory containing issue JSON files

        Returns:
            List of issue dictionaries
        """
        issues = []
        issue_dir = Path(issue_dir)

        if not issue_dir.exists():
            logger.warning(f"Issue directory not found: {issue_dir}")
            return issues

        for json_file in issue_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    issue = json.load(f)
                    issues.append(issue)
                    logger.info(f"Loaded issue: {json_file.name}")
            except Exception as e:
                logger.error(f"Failed to load {json_file}: {e}")

        return issues

    def analyze_issues(self, issues: List[Dict], query: str) -> Dict[str, Any]:
        """
        Analyze issues and extract insights

        Args:
            issues: List of issue dictionaries
            query: Search query used

        Returns:
            Analysis dictionary with insights
        """
        if not issues:
            return {
                'total_issues': 0,
                'status_breakdown': {},
                'priority_breakdown': {},
                'main_issue': None,
                'related_issues': [],
                'timeline': [],
                'keywords': []
            }

        # Status and priority breakdown
        status_counter = Counter(issue.get('status', 'Unknown') for issue in issues)
        priority_counter = Counter(issue.get('priority', 'Unknown') for issue in issues)

        # Identify main issue (highest priority + most recent if active)
        active_issues = [i for i in issues if 'Assigned' in i.get('status', '') or 'Open' in i.get('status', '')]
        high_priority = [i for i in active_issues if 'High' in i.get('priority', '') or 'Critical' in i.get('priority', '')]

        main_issue = None
        if high_priority:
            # Sort by date (most recent first)
            main_issue = sorted(high_priority, key=lambda x: x.get('created_date', ''), reverse=True)[0]
        elif active_issues:
            main_issue = sorted(active_issues, key=lambda x: x.get('created_date', ''), reverse=True)[0]
        elif issues:
            main_issue = sorted(issues, key=lambda x: x.get('created_date', ''), reverse=True)[0]

        # Related issues (all others)
        related_issues = [i for i in issues if i != main_issue]

        # Extract timeline from main issue
        timeline = []
        if main_issue:
            timeline = self._extract_timeline(main_issue)

        # Extract keywords from query and issues
        keywords = self._extract_keywords(query, issues)

        return {
            'total_issues': len(issues),
            'status_breakdown': dict(status_counter),
            'priority_breakdown': dict(priority_counter),
            'main_issue': main_issue,
            'related_issues': related_issues,
            'timeline': timeline,
            'keywords': keywords
        }

    def _extract_timeline(self, issue: Dict) -> List[Dict]:
        """Extract timeline events from issue comments and history"""
        timeline = []

        # Add creation date
        if issue.get('created_date'):
            timeline.append({
                'date': issue['created_date'],
                'event': '이슈 등록',
                'description': issue.get('title', '')
            })

        # Parse comments for timeline events
        comments = issue.get('comments', [])
        for comment in comments:
            date = comment.get('created_date', '')
            author = comment.get('author', '')
            content = comment.get('content', '')

            # Look for timeline keywords
            if any(keyword in content for keyword in ['패치', 'patch', '검증', '승인', '완료', '예정']):
                timeline.append({
                    'date': date,
                    'event': f"{author} 업데이트",
                    'description': content[:100] + '...' if len(content) > 100 else content
                })

        # Sort by date
        timeline.sort(key=lambda x: x.get('date', ''))

        return timeline

    def _extract_keywords(self, query: str, issues: List[Dict]) -> List[str]:
        """Extract relevant keywords from query and issues"""
        keywords = set()

        # From query
        query_words = query.upper().split()
        keywords.update(word.strip('+"\' ') for word in query_words if len(word) > 2)

        # From issue titles
        for issue in issues:
            title = issue.get('title', '')
            # Extract technical terms (usually in uppercase or mixed case)
            words = title.split()
            for word in words:
                if any(c.isupper() for c in word) and len(word) > 2:
                    keywords.add(word.strip('[]()'))

        return sorted(list(keywords))

    def generate_report(
        self,
        query: str,
        product: str,
        issues: List[Dict],
        output_file: Optional[Path] = None,
        language: str = "ko"
    ) -> str:
        """
        Generate comprehensive markdown report

        Args:
            query: Search query used
            product: Product name
            issues: List of issue dictionaries
            output_file: Optional output file path
            language: Report language (ko, ja, en)

        Returns:
            Generated markdown report as string
        """
        logger.info(f"Generating report for {len(issues)} issues...")

        # Analyze issues
        analysis = self.analyze_issues(issues, query)

        # Generate report sections
        if self.use_llm:
            logger.info("Using LLM-enhanced report generation")
            report = self._generate_llm_report(query, product, issues, analysis, language)
        else:
            logger.info("Using template-based report generation")
            report = self._generate_template_report(query, product, issues, analysis, language)

        # Save to file if specified
        if output_file:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved to: {output_file}")

        return report

    def _generate_template_report(
        self,
        query: str,
        product: str,
        issues: List[Dict],
        analysis: Dict,
        language: str
    ) -> str:
        """Generate report using templates (offline mode)"""

        # Report header
        report = self._generate_header(query, product, analysis, language)

        # Summary table
        report += self._generate_summary_table(issues, language)

        # Main issue analysis
        if analysis['main_issue']:
            report += self._generate_main_issue_section(analysis['main_issue'], language)

        # Related issues
        if analysis['related_issues']:
            report += self._generate_related_issues_section(analysis['related_issues'], language)

        # Conclusion and recommendations
        report += self._generate_conclusion_section(analysis, language)

        # Metadata footer
        report += self._generate_footer()

        return report

    def _generate_llm_report(
        self,
        query: str,
        product: str,
        issues: List[Dict],
        analysis: Dict,
        language: str
    ) -> str:
        """Generate LLM-enhanced report (online mode)"""

        # Start with template
        report = self._generate_template_report(query, product, issues, analysis, language)

        # Enhance key sections with LLM
        try:
            if analysis['main_issue']:
                main_issue = analysis['main_issue']

                # Generate enhanced root cause analysis
                root_cause_prompt = f"""
Analyze this issue and provide root cause analysis:
Title: {main_issue.get('title', '')}
Description: {main_issue.get('description', '')[:500]}

Provide:
1. Technical root cause
2. Impact analysis
3. Recommended solution approach
"""
                enhanced_analysis = self.llm_client.generate(root_cause_prompt)

                # Insert LLM analysis into report
                llm_section = f"\n\n### 🤖 LLM 심층 분석\n\n{enhanced_analysis}\n"
                report = report.replace("## 📝 과거 유사 이슈", llm_section + "\n## 📝 과거 유사 이슈")

        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            logger.info("Falling back to template-only report")

        return report

    def _generate_header(self, query: str, product: str, analysis: Dict, language: str) -> str:
        """Generate report header"""
        today = datetime.now().strftime("%Y-%m-%d")

        if language == "ko":
            title = f"# {product} 이슈 검색 결과\n\n"
            title += f"**검색일**: {today}\n"
            title += f"**검색 쿼리**: `{query}`\n"
            title += f"**검색 제품**: {product}\n"
            title += f"**검색 결과**: {analysis['total_issues']}개 이슈 발견\n\n"
            title += "---\n\n"
        elif language == "ja":
            title = f"# {product} 問題検索結果\n\n"
            title += f"**検索日**: {today}\n"
            title += f"**検索クエリ**: `{query}`\n"
            title += f"**製品**: {product}\n"
            title += f"**検索結果**: {analysis['total_issues']}件の問題\n\n"
            title += "---\n\n"
        else:  # en
            title = f"# {product} Issue Search Results\n\n"
            title += f"**Search Date**: {today}\n"
            title += f"**Query**: `{query}`\n"
            title += f"**Product**: {product}\n"
            title += f"**Results**: {analysis['total_issues']} issues found\n\n"
            title += "---\n\n"

        return title

    def _generate_summary_table(self, issues: List[Dict], language: str) -> str:
        """Generate summary table of all issues"""

        if language == "ko":
            section = "## 📊 검색 결과 요약\n\n"
            section += "| Issue ID | 제목 | 상태 | 우선순위 | 등록일 |\n"
            section += "|----------|------|------|----------|--------|\n"
        elif language == "ja":
            section = "## 📊 検索結果概要\n\n"
            section += "| Issue ID | タイトル | ステータス | 優先度 | 登録日 |\n"
            section += "|----------|----------|------------|--------|--------|\n"
        else:
            section = "## 📊 Search Results Summary\n\n"
            section += "| Issue ID | Title | Status | Priority | Created |\n"
            section += "|----------|-------|--------|----------|----------|\n"

        # Sort: Active High priority first, then by date
        sorted_issues = sorted(
            issues,
            key=lambda x: (
                0 if 'High' in x.get('priority', '') and 'Assigned' in x.get('status', '') else 1,
                x.get('created_date', '')
            ),
            reverse=True
        )

        for issue in sorted_issues:
            issue_id = issue.get('issue_id', 'N/A')
            title = issue.get('title', 'No title')[:50]
            status = issue.get('status', 'Unknown')
            priority = issue.get('priority', 'Normal')
            created = issue.get('created_date', 'N/A')

            # Highlight high priority active issues
            if 'High' in priority and 'Assigned' in status:
                section += f"| **{issue_id}** | {title} | **{status}** | **{priority}** | {created} |\n"
            else:
                section += f"| {issue_id} | {title} | {status} | {priority} | {created} |\n"

        section += "\n---\n\n"
        return section

    def _generate_main_issue_section(self, issue: Dict, language: str) -> str:
        """Generate detailed analysis of main issue"""

        if language == "ko":
            section = f"## 🔥 주요 이슈 #{issue.get('issue_id', 'N/A')}"
            if 'Assigned' in issue.get('status', ''):
                section += " (진행중"
                if 'High' in issue.get('priority', ''):
                    section += " - HIGH Priority"
                section += ")\n\n"
            else:
                section += "\n\n"

            section += "### 📌 이슈 개요\n\n"
            section += f"**제목**: {issue.get('title', 'N/A')}\n"
            section += f"**상태**: {issue.get('status', 'Unknown')}\n"
            section += f"**우선순위**: {issue.get('priority', 'Normal')}\n"
            section += f"**담당자**: {issue.get('assignee', 'Unassigned')}\n"
            section += f"**제품**: {issue.get('product', 'N/A')}\n\n"

            section += "### 🐛 이슈 내용\n\n"
            description = issue.get('description', 'No description available')
            section += f"{description[:1000]}\n\n"

            if issue.get('comments'):
                section += "### 💡 해결 방안\n\n"
                # Show most recent comments
                recent_comments = issue['comments'][-3:]
                for comment in recent_comments:
                    author = comment.get('author', 'Unknown')
                    date = comment.get('created_date', '')
                    content = comment.get('content', '')
                    section += f"**{author}** ({date}):\n{content[:500]}\n\n"

        else:  # English/Japanese similar structure
            section = f"## 🔥 Main Issue #{issue.get('issue_id', 'N/A')}\n\n"
            section += "### 📌 Overview\n\n"
            section += f"**Title**: {issue.get('title', 'N/A')}\n"
            section += f"**Status**: {issue.get('status', 'Unknown')}\n"
            section += f"**Priority**: {issue.get('priority', 'Normal')}\n\n"

            section += "### 🐛 Description\n\n"
            description = issue.get('description', 'No description available')
            section += f"{description[:1000]}\n\n"

        section += "---\n\n"
        return section

    def _generate_related_issues_section(self, related_issues: List[Dict], language: str) -> str:
        """Generate section for related/resolved issues"""

        if language == "ko":
            section = "## 📋 관련 이슈\n\n"
        elif language == "ja":
            section = "## 📋 関連問題\n\n"
        else:
            section = "## 📋 Related Issues\n\n"

        for issue in related_issues[:3]:  # Limit to 3 most relevant
            issue_id = issue.get('issue_id', 'N/A')
            title = issue.get('title', 'No title')
            status = issue.get('status', 'Unknown')

            if language == "ko":
                section += f"### 이슈 #{issue_id} ({'해결됨' if 'Closed' in status else status})\n\n"
                section += f"**제목**: {title}\n\n"
            else:
                section += f"### Issue #{issue_id} ({status})\n\n"
                section += f"**Title**: {title}\n\n"

            # Add brief description
            desc = issue.get('description', '')[:300]
            if desc:
                section += f"{desc}...\n\n"

        section += "---\n\n"
        return section

    def _generate_conclusion_section(self, analysis: Dict, language: str) -> str:
        """Generate conclusion and recommendations"""

        if language == "ko":
            section = "## 🎯 결론\n\n"
            section += f"### {analysis['keywords'][0] if analysis['keywords'] else '이슈'} 현황\n\n"

            active_count = sum(1 for status in analysis['status_breakdown'].keys() if 'Assigned' in status or 'Open' in status)
            resolved_count = sum(1 for status in analysis['status_breakdown'].keys() if 'Closed' in status)

            section += f"1. **주요 이슈 {active_count}건 진행 중**\n"
            if analysis['main_issue']:
                section += f"   - {analysis['main_issue'].get('title', 'N/A')}\n"
                if 'High' in analysis['main_issue'].get('priority', ''):
                    section += f"   - 업무 영향도 높음 (High Priority)\n"
            section += f"\n2. **과거 유사 이슈 {resolved_count}건 해결 완료**\n\n"

            section += "3. **향후 대응 방향**\n"
            section += "   - 진행 중인 이슈 모니터링\n"
            section += "   - 해결된 이슈의 패치 적용 여부 확인\n"
            section += "   - 유사 문제 재발 방지를 위한 가이드 정립\n\n"

        else:
            section = "## 🎯 Conclusion\n\n"
            section += f"### Issue Status Summary\n\n"
            section += f"- **Total Issues**: {analysis['total_issues']}\n"
            section += f"- **Status Breakdown**: {analysis['status_breakdown']}\n"
            section += f"- **Priority Breakdown**: {analysis['priority_breakdown']}\n\n"

        section += "---\n\n"
        return section

    def _generate_footer(self) -> str:
        """Generate report footer with metadata"""
        today = datetime.now().strftime("%Y-%m-%d")

        footer = f"**보고서 작성일**: {today}\n"
        footer += f"**작성자**: IMS Report Generator (자동 생성)\n"
        footer += f"**데이터 출처**: TmaxSoft IMS (https://ims.tmaxsoft.com)\n"

        return footer
