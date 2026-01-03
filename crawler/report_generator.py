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
from .category_extractor import CategoryExtractor

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
        self.category_extractor = CategoryExtractor(llm_client)

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
            # Skip search_result.json - it's not an issue file
            if json_file.name == "search_result.json":
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    issue = json.load(f)
                    issues.append(issue)
                    logger.info(f"Loaded issue: {json_file.name}")
            except Exception as e:
                logger.error(f"Failed to load {json_file}: {e}")

        return issues

    def analyze_issues(self, issues: List[Dict], query: str, search_results: Dict = None) -> Dict[str, Any]:
        """
        Analyze issues and extract insights

        Args:
            issues: List of issue dictionaries
            query: Search query used
            search_results: Optional search results from search_result.json

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

        # If search results exist, use them to determine main issue and order
        if search_results and 'results' in search_results and search_results['results']:
            # Create issue_id to issue mapping
            issue_map = {issue.get('issue_id'): issue for issue in issues}

            # Get ordered issues from search results
            ordered_issues = []
            for result in search_results['results']:
                issue_id = result.get('issue_id')
                if issue_id in issue_map:
                    ordered_issues.append(issue_map[issue_id])

            # Main issue is the top search result
            main_issue = ordered_issues[0] if ordered_issues else None

            # Related issues are the rest
            related_issues = ordered_issues[1:] if len(ordered_issues) > 1 else []

        else:
            # Fallback to original logic if no search results
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
        language: str = "ko",
        session_path: Optional[Path] = None,
        full_issues: bool = False,
        create_html: bool = False
    ) -> str:
        """
        Generate comprehensive markdown report

        Args:
            query: Search query used
            product: Product name
            issues: List of issue dictionaries
            output_file: Optional output file path
            language: Report language (ko, ja, en)
            session_path: Optional session folder path for search_result.json
            full_issues: Analyze all search results instead of just main issue
            create_html: Generate HTML version with collapsible sections

        Returns:
            Generated markdown report as string
        """
        logger.info(f"Generating report for {len(issues)} issues...")

        # Load search results if available (must be done before analyze_issues)
        search_results = None
        if session_path:
            search_result_file = Path(session_path) / "search_result.json"
            if search_result_file.exists():
                try:
                    with open(search_result_file, 'r', encoding='utf-8') as f:
                        search_results = json.load(f)
                    logger.info(f"Loaded search results from: {search_result_file}")
                except Exception as e:
                    logger.warning(f"Failed to load search results: {e}")

        # Analyze issues (with search results if available)
        analysis = self.analyze_issues(issues, query, search_results)

        # Add search results to analysis for conclusion section
        if search_results:
            analysis['search_results'] = search_results

        # Generate report sections
        if self.use_llm:
            logger.info("Using LLM-enhanced report generation (with category extraction)")
            report = self._generate_llm_report(query, product, issues, analysis, language, use_llm=True, full_issues=full_issues)
        else:
            logger.info("Using template-based report generation (with keyword-based category extraction)")
            report = self._generate_template_report(query, product, issues, analysis, language, use_llm=False, full_issues=full_issues)

        # Save to file if specified
        if output_file:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved to: {output_file}")

            # Generate HTML version if requested
            if create_html:
                html_output = output_file.with_suffix('.html')
                html_content = self._generate_html_report(report, query, product, analysis, language)
                with open(html_output, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"HTML report saved to: {html_output}")

        return report

    def _generate_template_report(
        self,
        query: str,
        product: str,
        issues: List[Dict],
        analysis: Dict,
        language: str,
        use_llm: bool = False,
        full_issues: bool = False
    ) -> str:
        """Generate report using templates (offline mode)"""

        # Report header
        report = self._generate_header(query, product, analysis, language)

        # Summary table (use search results order if available)
        search_results = analysis.get('search_results')
        report += self._generate_summary_table(issues, language, search_results)

        # Issue analysis
        if full_issues and search_results and 'results' in search_results:
            # Analyze all search results
            report += "\n\n## 🔥 이슈 분석 (전체)\n\n"
            logger.info(f"Analyzing all {len(search_results['results'])} issues (full_issues=True)")

            issue_map = {issue.get('issue_id'): issue for issue in issues}
            for idx, result in enumerate(search_results['results'], 1):
                issue_id = result.get('issue_id')
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    report += self._generate_main_issue_section(issue, language, use_llm, issue_number=idx)
                    report += "\n---\n\n"
        else:
            # Main issue analysis only (with category extraction)
            if analysis['main_issue']:
                report += self._generate_main_issue_section(analysis['main_issue'], language, use_llm)

        # Related issues
        if not full_issues and analysis['related_issues']:
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
        language: str,
        use_llm: bool = True,
        full_issues: bool = False
    ) -> str:
        """Generate LLM-enhanced report (online mode)"""

        # Start with template (with LLM-based category extraction)
        report = self._generate_template_report(query, product, issues, analysis, language, use_llm, full_issues)

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

    def _generate_summary_table(self, issues: List[Dict], language: str, search_results: Dict = None) -> str:
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

        # If search results exist, use search score order
        if search_results and 'results' in search_results and search_results['results']:
            # Create issue_id to issue mapping
            issue_map = {issue.get('issue_id'): issue for issue in issues}

            # Order issues by search results
            sorted_issues = []
            for result in search_results['results']:
                issue_id = result.get('issue_id')
                if issue_id in issue_map:
                    sorted_issues.append(issue_map[issue_id])
        else:
            # Default: Sort by Active High priority first, then by date
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

    def _generate_main_issue_section(self, issue: Dict, language: str, use_llm: bool = False, issue_number: int = None) -> str:
        """Generate detailed analysis of main issue with categorized extraction"""

        if language == "ko":
            # Header with status badge
            status = issue.get('status', 'Unknown')
            priority = issue.get('priority', 'Normal')

            # Issue number prefix if provided
            number_prefix = f"[{issue_number}] " if issue_number else ""

            status_badge = ""
            if 'Assigned' in status or 'Open' in status:
                status_badge = "🔴 진행중"
            elif 'Approved' in status:
                status_badge = "🟡 승인됨"
            elif 'Closed' in status:
                status_badge = "🟢 해결됨"
            else:
                status_badge = f"⚪ {status}"

            priority_badge = ""
            if 'High' in priority or 'Critical' in priority:
                priority_badge = "🔥 높음"
            elif 'Low' in priority:
                priority_badge = "🔵 낮음"
            else:
                priority_badge = f"⚫ {priority}"

            if not issue_number:
                section = f"## 🔥 주요 이슈 분석\n\n"
            else:
                section = ""
            section += f"### {number_prefix}Issue #{issue.get('issue_id', 'N/A')} - {status_badge} | {priority_badge}\n\n"

            # Summary box
            section += "> **📋 요약**\n>\n"
            section += f"> **제목**: {issue.get('title', 'N/A')}\n"
            section += f"> **제품**: {issue.get('product', 'N/A')}\n"
            section += f"> **담당자**: {issue.get('assignee', 'Unassigned')}\n"
            section += f"> **등록일**: {issue.get('created_date', 'N/A')}\n\n"

            # Metadata table
            section += "| 항목 | 정보 |\n"
            section += "|------|------|\n"
            section += f"| 🆔 Issue ID | {issue.get('issue_id', 'N/A')} |\n"
            section += f"| 📦 제품 | {issue.get('product', 'N/A')} |\n"
            section += f"| 📊 상태 | {status} |\n"
            section += f"| ⚡ 우선순위 | {priority} |\n"
            section += f"| 👤 담당자 | {issue.get('assignee', 'Unassigned')} |\n"
            section += f"| 📅 등록일 | {issue.get('created_date', 'N/A')} |\n\n"

            section += "---\n\n"

            # Extract categories
            categories = self.category_extractor.extract_categories(issue, use_llm=use_llm, language=language)

            # 현상 (Symptom) - Enhanced format
            if categories.get('symptom'):
                section += "### 🔍 현상 (Symptom)\n\n"
                section += "<details>\n<summary><b>발견된 증상 및 문제 현상</b></summary>\n\n"
                for i, symptom in enumerate(categories['symptom'], 1):
                    section += f"{i}. **{symptom[:100]}**\n"
                    if len(symptom) > 100:
                        section += f"   \n   {symptom[100:]}\n"
                    section += "\n"
                section += "</details>\n\n"
            else:
                # Fallback to description if no symptoms extracted
                section += "### 🐛 이슈 내용\n\n"
                description = issue.get('description', 'No description available')
                section += f"```\n{description[:1000]}\n```\n\n"

            # 원인 (Cause) - Enhanced format
            if categories.get('cause'):
                section += "### 🔎 원인 분석 (Root Cause)\n\n"
                section += "```diff\n"
                for i, cause in enumerate(categories['cause'], 1):
                    section += f"- [{i}] {cause}\n"
                section += "```\n\n"

            # 대응방안 (Solution) - Enhanced format with action items
            if categories.get('solution'):
                section += "### 💡 대응방안 및 조치사항 (Solution)\n\n"
                section += "#### ✅ 권장 조치사항\n\n"
                for i, solution in enumerate(categories['solution'], 1):
                    section += f"**{i}. 조치 항목**\n"
                    section += f"- [ ] {solution}\n\n"
            elif issue.get('comments'):
                # Fallback to comments if no solutions extracted
                section += "### 💡 해결 방안\n\n"
                recent_comments = issue['comments'][-3:]
                for comment in recent_comments:
                    author = comment.get('author', 'Unknown')
                    date = comment.get('created_date', '')
                    content = comment.get('content', '')
                    section += f"**💬 {author}** ({date}):\n```\n{content[:500]}\n```\n\n"

            # Analysis metadata footer
            method = categories.get('method', 'unknown')
            confidence = categories.get('confidence', 0.0)

            section += "---\n\n"
            section += "**📊 분석 메타데이터**\n\n"
            section += f"- **분석 방법**: {method.upper()}\n"
            section += f"- **신뢰도**: {confidence:.0%}\n"
            section += f"- **추출된 카테고리**: {len([k for k, v in categories.items() if v and k in ['symptom', 'cause', 'solution']])}개\n\n"

        else:  # English/Japanese similar structure
            section = f"## 🔥 Main Issue #{issue.get('issue_id', 'N/A')}\n\n"
            section += "### 📌 Overview\n\n"
            section += f"**Title**: {issue.get('title', 'N/A')}\n"
            section += f"**Status**: {issue.get('status', 'Unknown')}\n"
            section += f"**Priority**: {issue.get('priority', 'Normal')}\n\n"

            # Extract categories
            categories = self.category_extractor.extract_categories(issue, use_llm=use_llm, language=language)

            # Symptom
            if categories.get('symptom'):
                section += "### 🔍 Symptom\n\n"
                for symptom in categories['symptom']:
                    section += f"- {symptom}\n"
                section += "\n"

            # Cause
            if categories.get('cause'):
                section += "### 🔎 Cause\n\n"
                for cause in categories['cause']:
                    section += f"- {cause}\n"
                section += "\n"

            # Solution
            if categories.get('solution'):
                section += "### 💡 Solution\n\n"
                for solution in categories['solution']:
                    section += f"- {solution}\n"
                section += "\n"

            method = categories.get('method', 'unknown')
            confidence = categories.get('confidence', 0.0)
            section += f"\n> 📊 Analysis method: {method} (confidence: {confidence:.0%})\n\n"

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

        # Check if search results are available
        search_results = analysis.get('search_results')

        if language == "ko":
            section = "## 🎯 결론\n\n"

            # If search results exist, use them for conclusion
            if search_results and 'results' in search_results:
                results = search_results['results']
                section += f"### 검색 결과 기반 분석 (쿼리: {search_results.get('query', 'N/A')})\n\n"

                # Count issues by status from search results
                active_issues = [r for r in results if 'Assigned' in r.get('status', '') or 'Open' in r.get('status', '')]
                resolved_issues = [r for r in results if 'Closed' in r.get('status', '')]
                high_priority_issues = [r for r in results if 'High' in r.get('priority', '') or 'Critical' in r.get('priority', '')]

                section += f"1. **검색된 이슈 총 {len(results)}건**\n"
                section += f"   - 진행 중: {len(active_issues)}건\n"
                section += f"   - 해결 완료: {len(resolved_issues)}건\n"
                if high_priority_issues:
                    section += f"   - 높은 우선순위: {len(high_priority_issues)}건\n"
                section += "\n"

                # Show all search results (ordered by score)
                if results:
                    section += "2. **상위 검색 결과**\n"
                    for i, result in enumerate(results, 1):
                        section += f"   {i}. [{result.get('issue_id', 'N/A')}] {result.get('title', 'N/A')} (점수: {result.get('score', 0):.3f})\n"
                    section += "\n"

                # Recommendations based on search results
                section += "3. **권장 사항**\n"
                if active_issues:
                    section += "   - 진행 중인 이슈 우선 검토 필요\n"
                if high_priority_issues:
                    section += "   - 높은 우선순위 이슈 즉시 대응\n"
                if resolved_issues:
                    section += "   - 해결된 이슈의 솔루션 참고 가능\n"
                section += "   - 검색 결과의 상세 내용 확인 및 적용\n\n"

            else:
                # Fallback to original logic if no search results
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

            if search_results and 'results' in search_results:
                results = search_results['results']
                section += f"### Search Results Analysis (Query: {search_results.get('query', 'N/A')})\n\n"
                section += f"- **Total Results**: {len(results)}\n"
                section += f"- **Search Score Range**: {results[0]['score']:.3f} - {results[-1]['score']:.3f}\n\n"
            else:
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

    def _generate_html_report(self, markdown_content: str, query: str, product: str, analysis: Dict, language: str) -> str:
        """
        Generate HTML report with collapsible sections and professional styling

        Args:
            markdown_content: Markdown report content
            query: Search query
            product: Product name
            analysis: Analysis results dictionary
            language: Report language

        Returns:
            HTML formatted report
        """
        import re

        # Convert markdown to HTML (basic conversion)
        html_content = markdown_content

        # Headers
        html_content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)

        # Bold and inline code
        html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
        html_content = re.sub(r'`(.*?)`', r'<code>\1</code>', html_content)

        # Lists
        html_content = re.sub(r'^\- (.*?)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)

        # Convert table markdown to HTML
        html_content = self._convert_markdown_tables_to_html(html_content)

        # Wrap issue sections in collapsible containers
        html_content = self._wrap_issues_in_collapsible(html_content)

        # Links
        html_content = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank">\1</a>', html_content)

        # Paragraphs
        html_content = re.sub(r'\n\n', '</p><p>', html_content)
        html_content = '<p>' + html_content + '</p>'

        # Fix empty paragraphs
        html_content = re.sub(r'<p>\s*</p>', '', html_content)
        html_content = re.sub(r'<p>(<h[123]>)', r'\1', html_content)
        html_content = re.sub(r'(</h[123]>)</p>', r'\1', html_content)
        html_content = re.sub(r'<p>(<table)', r'\1', html_content)
        html_content = re.sub(r'(</table>)</p>', r'\1', html_content)

        # Create full HTML document
        today = datetime.now().strftime("%Y-%m-%d")

        html_template = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{product} IMS 이슈 검색 결과 - {query}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}

        .header-meta {{
            font-size: 1.1em;
            opacity: 0.95;
        }}

        .header-meta strong {{
            color: #ffd700;
        }}

        .content {{
            padding: 40px;
        }}

        h2 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin: 30px 0 20px 0;
            font-size: 1.8em;
        }}

        h3 {{
            color: #764ba2;
            margin: 25px 0 15px 0;
            font-size: 1.4em;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 15px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        tbody tr:hover {{
            background: #f8f9ff;
            transition: background 0.3s ease;
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        .issue-collapsible {{
            margin: 30px 0;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s ease;
        }}

        .issue-collapsible:hover {{
            border-color: #667eea;
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.2);
        }}

        .issue-collapsible summary {{
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            padding: 20px;
            cursor: pointer;
            font-weight: 600;
            font-size: 1.2em;
            color: #667eea;
            user-select: none;
            display: flex;
            align-items: center;
            transition: background 0.3s ease;
        }}

        .issue-collapsible summary:hover {{
            background: linear-gradient(135deg, #e8ecff 0%, #d8e0ff 100%);
        }}

        .issue-collapsible summary::marker {{
            color: #667eea;
            font-size: 1.3em;
        }}

        .issue-collapsible[open] summary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        .issue-content {{
            padding: 25px;
            background: #fafbff;
        }}

        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin: 0 5px;
        }}

        .badge-status {{
            background: #667eea;
            color: white;
        }}

        .badge-priority {{
            background: #764ba2;
            color: white;
        }}

        code {{
            background: #f4f4f4;
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }}

        .footer {{
            background: #f8f9ff;
            padding: 30px;
            text-align: center;
            border-top: 3px solid #667eea;
            color: #666;
        }}

        hr {{
            border: none;
            border-top: 2px solid #eee;
            margin: 30px 0;
        }}

        a {{
            color: #667eea;
            text-decoration: none;
            transition: color 0.3s ease;
        }}

        a:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}

        @media print {{
            body {{
                background: white;
            }}
            .container {{
                box-shadow: none;
            }}
            .issue-collapsible {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 {product} IMS 이슈 검색 결과</h1>
            <div class="header-meta">
                <strong>검색 쿼리:</strong> {query} |
                <strong>검색일:</strong> {today} |
                <strong>결과:</strong> {analysis.get('total_issues', 0)}개 이슈
            </div>
        </div>

        <div class="content">
            {html_content}
        </div>

        <div class="footer">
            <p><strong>보고서 작성일:</strong> {today}</p>
            <p><strong>작성자:</strong> IMS Report Generator (자동 생성)</p>
            <p><strong>데이터 출처:</strong> <a href="https://ims.tmaxsoft.com">TmaxSoft IMS</a></p>
        </div>
    </div>
</body>
</html>"""

        return html_template

    def _convert_markdown_tables_to_html(self, content: str) -> str:
        """Convert markdown tables to HTML tables"""
        import re

        # Find all markdown tables
        table_pattern = r'(\|.+\|[\r\n]+\|[-:| ]+\|[\r\n]+(?:\|.+\|[\r\n]+)*)'

        def convert_table(match):
            table_md = match.group(1)
            lines = [line.strip() for line in table_md.split('\n') if line.strip()]

            if len(lines) < 2:
                return table_md

            # Parse header
            headers = [cell.strip() for cell in lines[0].split('|') if cell.strip()]

            # Build HTML table
            html = '<table>\n<thead>\n<tr>\n'
            for header in headers:
                html += f'<th>{header}</th>\n'
            html += '</tr>\n</thead>\n<tbody>\n'

            # Parse body rows (skip separator line)
            for line in lines[2:]:
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                if cells:
                    html += '<tr>\n'
                    for cell in cells:
                        html += f'<td>{cell}</td>\n'
                    html += '</tr>\n'

            html += '</tbody>\n</table>\n'
            return html

        return re.sub(table_pattern, convert_table, content)

    def _wrap_issues_in_collapsible(self, content: str) -> str:
        """Wrap each issue section in a collapsible details element"""
        import re

        # Find issue sections
        issue_pattern = r'(<h3>.*?Issue #\d+.*?</h3>)(.*?)(?=<h3>.*?Issue #\d+|<h2>|$)'

        def wrap_issue(match):
            header = match.group(1)
            body = match.group(2)

            # Extract issue title from header
            title_match = re.search(r'<h3>(.*?)</h3>', header)
            title = title_match.group(1) if title_match else "Issue"

            return f'''<details class="issue-collapsible" open>
<summary>{title}</summary>
<div class="issue-content">
{body}
</div>
</details>'''

        return re.sub(issue_pattern, wrap_issue, content, flags=re.DOTALL)
