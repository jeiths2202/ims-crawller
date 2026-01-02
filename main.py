"""
IMS Crawler - Main CLI Interface
Command-line tool for crawling IMS issues
"""
import sys
import io
import logging
from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from config import settings
from crawler import IMSScraper
from crawler.nl_parser import NaturalLanguageParser, is_ims_syntax, ParsingError
from crawler.llm_client import OllamaClient, LLMConfig
from crawler.history_manager import HistoryManager
from crawler.query_builder_ui import InteractiveQueryBuilder
from crawler.analytics_engine import AnalyticsEngine
from crawler.report_generator import ReportGenerator
from crawler.llm_client import get_default_llm_client
from crawler.utils import create_crawl_folder_name, get_latest_crawl_folder

# Fix Windows console encoding for Korean/Japanese characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup rich console
console = Console()

# Setup logging with rich handler
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.0', prog_name='IMS Crawler')
def cli():
    """
    🕷️  IMS Crawler - Crawl and extract issues from IMS system

    A tool for crawling issue management systems and extracting structured data
    for knowledge base integration and troubleshooting.
    """
    pass


@cli.command()
@click.option(
    '--product', '-p',
    required=True,
    help='Product name to filter by (e.g., "Tibero", "JEUS")'
)
@click.option(
    '--keywords', '-k',
    required=True,
    help='''Search keywords using IMS syntax:

    \b
    OR search: "Tmax Tibero" (space-separated)
    AND search: "IMS +error" (+ before required word)
    Exact phrase: "'error log'" (single quotes)
    Combined: "Tmax 'error log' +Tibero"
    Issue number: "348115" or "+348115"
    '''
)
@click.option(
    '--max-results', '-m',
    default=settings.DEFAULT_MAX_RESULTS,
    type=int,
    help=f'Maximum number of issues to crawl (default: {settings.DEFAULT_MAX_RESULTS})'
)
@click.option(
    '--output-dir', '-o',
    default=str(settings.OUTPUT_DIR),
    type=click.Path(),
    help='Output directory for JSON files'
)
@click.option(
    '--headless/--no-headless',
    default=True,
    help='Run browser in headless mode (default: headless)'
)
@click.option(
    '--crawl-related/--no-crawl-related',
    default=False,
    help='Crawl related issues recursively (default: no)'
)
@click.option(
    '--max-depth',
    default=2,
    type=int,
    help='Maximum depth for related issue crawling (default: 2)'
)
@click.option(
    '--no-confirm',
    is_flag=True,
    default=False,
    help='Skip natural language parsing confirmation (batch mode)'
)
@click.option(
    '--no-llm',
    is_flag=True,
    default=False,
    help='Disable LLM fallback, use rules-only parsing (faster)'
)
def crawl(product, keywords, max_results, output_dir, headless, crawl_related, max_depth, no_confirm, no_llm):
    """
    Crawl IMS issues based on search criteria

    \b
    IMS Search Syntax Guide:

    1) OR search (space-separated keywords):
       "Tmax Tibero" → finds Tmax OR Tibero

    2) AND search (+ before required word, no space):
       "IMS +error" → finds IMS AND error
       "+connection +timeout" → finds both connection AND timeout

    3) Exact phrase (enclosed in single quotes):
       "'error log'" → exact phrase "error log"
       "'out of memory'" → exact phrase "out of memory"

    4) Combined search:
       "Tmax 'error log' +Tibero" → Tmax OR ('error log' AND Tibero)
       "database +error +'connection timeout'" → database AND error AND exact phrase

    5) Issue number search:
       "348115" → search by issue number
       "+348115" → required issue number

    \b
    Examples:

    \b
    # OR search: Find connection OR timeout issues
    $ python main.py crawl -p "Tibero" -k "connection timeout" -m 50

    \b
    # AND search: Find issues with both error AND crash
    $ python main.py crawl -p "OpenFrame" -k "+error +crash" -m 50

    \b
    # Exact phrase search
    $ python main.py crawl -p "JEUS" -k "'out of memory'" -m 100

    \b
    # Combined search: IMS AND (error OR crash) AND exact phrase
    $ python main.py crawl -p "Tibero" -k "error crash +IMS +'connection timeout'" -m 50

    \b
    # Search by issue number
    $ python main.py crawl -p "OpenFrame" -k "348115" -m 1

    \b
    # Multiple issue numbers (OR search)
    $ python main.py crawl -p "OpenFrame" -k "348115 347878 346525" -m 10

    \b
    Natural Language Queries (Phase 2 & 3):

    \b
    # English: Find error and crash (parsed to: +error +crash)
    $ python main.py crawl -p "Tibero" -k "find error and crash" -m 50

    \b
    # Korean: 에러와 크래시 찾기 (parsed to: +에러 +크래시)
    $ python main.py crawl -p "JEUS" -k "에러와 크래시 찾아줘" -m 50

    \b
    # Japanese: エラーとクラッシュ (parsed to: +エラー +クラッシュ)
    $ python main.py crawl -p "OpenFrame" -k "エラーとクラッシュを検索" -m 50

    \b
    # Batch mode: Skip confirmation
    $ python main.py crawl -p "Tibero" -k "find connection timeout" --no-confirm -m 50

    \b
    # Rules-only: Disable LLM fallback for faster parsing
    $ python main.py crawl -p "JEUS" -k "show errors" --no-llm -m 50

    \b
    # Crawl with related issues (parallel processing)
    $ python main.py crawl -p "OpenFrame" -k "5213" --crawl-related --max-depth 2 -m 10
    """

    # Validate configuration
    if not settings.IMS_BASE_URL:
        console.print("[red]❌ Error: IMS_BASE_URL not configured[/red]")
        console.print("Please set IMS_BASE_URL in .env file")
        sys.exit(1)

    if not settings.IMS_USERNAME or not settings.IMS_PASSWORD:
        console.print("[red]❌ Error: IMS credentials not configured[/red]")
        console.print("Please set IMS_USERNAME and IMS_PASSWORD in .env file")
        sys.exit(1)

    # Natural Language Query Parsing
    final_query = keywords  # Default: use keywords as-is
    parse_method = "direct"  # Track parsing method for history
    parse_language = "en"  # Default language
    parse_confidence = 1.0  # Direct IMS syntax = 100% confidence
    start_time = None  # Track execution time

    if is_ims_syntax(keywords):
        # IMS syntax detected - pass through
        console.print("[green]✓[/green] IMS syntax detected, using as-is")
        final_query = keywords
    else:
        # Natural language detected - parse it
        console.print("[yellow]⚙[/yellow]  Parsing natural language query...")

        try:
            # Initialize LLM client if enabled (Phase 3)
            llm_client = None
            if settings.USE_LLM and not no_llm:
                llm_config = LLMConfig(
                    model=settings.LLM_MODEL,
                    base_url=settings.LLM_BASE_URL,
                    timeout=settings.LLM_TIMEOUT,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS
                )
                llm_client = OllamaClient(llm_config)

                if llm_client.available:
                    console.print(f"[dim]LLM fallback enabled: {settings.LLM_MODEL}[/dim]")
                else:
                    console.print(f"[yellow]⚠[/yellow] LLM server not available, using rules only")
                    llm_client = None
            elif no_llm:
                console.print("[dim]LLM disabled (--no-llm flag), using rules only[/dim]")

            # Initialize NL parser
            nl_parser = NaturalLanguageParser(llm_client=llm_client)

            # Parse query
            result = nl_parser.parse(keywords)

            # Update tracking variables
            parse_method = result.method
            parse_language = result.language
            parse_confidence = result.confidence

            # Show parsing result
            parse_table = Table(title="🔍 Query Parsing Result", show_header=False)
            parse_table.add_column("Field", style="cyan")
            parse_table.add_column("Value", style="green")

            parse_table.add_row("Original Query", keywords)
            parse_table.add_row("Parsed IMS Syntax", result.ims_query)
            parse_table.add_row("Language", result.language.upper())
            parse_table.add_row("Method", result.method.capitalize())
            parse_table.add_row("Confidence", f"{result.confidence:.1%}")
            parse_table.add_row("Explanation", result.explanation)

            console.print()
            console.print(parse_table)
            console.print()

            # Confidence warning
            if result.confidence < 0.8:
                console.print(
                    f"[yellow]⚠ Low confidence ({result.confidence:.1%}). "
                    "Please review parsed query carefully.[/yellow]"
                )
                console.print()

            # User confirmation (unless --no-confirm)
            if not no_confirm:
                confirmed = click.confirm(
                    "Continue with this parsed query?",
                    default=True
                )

                if not confirmed:
                    console.print("[red]✗[/red] Query parsing cancelled by user")
                    console.print()
                    console.print(
                        "[cyan]Tip:[/cyan] You can use IMS syntax directly to skip parsing:\n"
                        f"  python main.py crawl -k '{result.ims_query}' -p \"{product}\" ..."
                    )
                    sys.exit(0)

            final_query = result.ims_query
            console.print("[green]✓[/green] Using parsed query")
            console.print()

        except ParsingError as e:
            console.print(f"[red]✗[/red] Parsing failed: {e}")
            console.print()
            console.print(
                "[cyan]Tip:[/cyan] Try using IMS syntax directly. "
                "See SEARCH_GUIDE.md for syntax reference."
            )
            sys.exit(1)

    # Create session folder with timestamp
    from datetime import datetime
    session_folder_name = create_crawl_folder_name(product, final_query, datetime.now())
    session_folder = Path("data/crawl_sessions") / session_folder_name
    session_folder.mkdir(parents=True, exist_ok=True)

    # Create attachments subfolder within session
    attachments_folder = session_folder / "attachments"
    attachments_folder.mkdir(parents=True, exist_ok=True)

    # Display crawl configuration
    config_table = Table(title="🔧 Crawl Configuration", show_header=False)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Product", product)
    config_table.add_row("Search Query", final_query)
    config_table.add_row("Max Results", str(max_results))
    config_table.add_row("Session Folder", str(session_folder))
    config_table.add_row("Headless", "Yes" if headless else "No")
    config_table.add_row("Crawl Related Issues", "Yes" if crawl_related else "No")
    if crawl_related:
        config_table.add_row("Max Depth", str(max_depth))

    console.print(config_table)
    console.print()

    try:
        # Initialize scraper
        console.print("[yellow]🚀 Initializing crawler...[/yellow]")

        # Track execution time
        import time
        start_time = time.time()

        with IMSScraper(
            base_url=settings.IMS_BASE_URL,
            username=settings.IMS_USERNAME,
            password=settings.IMS_PASSWORD,
            output_dir=session_folder,
            attachments_dir=attachments_folder,
            headless=headless,
            cookie_file=settings.COOKIE_FILE
        ) as scraper:

            # Execute crawl
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:

                task = progress.add_task(
                    "[cyan]Crawling issues...",
                    total=max_results
                )

                try:
                    issues = scraper.crawl(
                        product=product,
                        keywords=final_query,
                        max_results=max_results,
                        crawl_related=crawl_related,
                        max_depth=max_depth
                    )

                    progress.update(task, completed=len(issues))

                    # Display results
                    console.print()
                    result_msg = f"[green]✅ Successfully crawled {len(issues)} issues[/green]"
                    if crawl_related:
                        result_msg += f"\n[yellow]📎 Including related issues (max depth: {max_depth})[/yellow]"
                    result_msg += f"\n[cyan]📁 Session folder: {session_folder}[/cyan]"

                    console.print(Panel.fit(
                        result_msg,
                        title="✨ Crawl Complete",
                        border_style="green"
                    ))

                    # Display sample of crawled issues
                    if issues:
                        results_table = Table(title="📊 Crawled Issues (Sample)")
                        results_table.add_column("Issue ID", style="cyan")
                        results_table.add_column("Title", style="white", max_width=50)
                        results_table.add_column("Status", style="yellow")

                        for issue in issues[:10]:  # Show first 10
                            results_table.add_row(
                                issue.get('issue_id', 'N/A'),
                                issue.get('title', 'N/A')[:50],
                                issue.get('status', 'N/A')
                            )

                        console.print()
                        console.print(results_table)

                        if len(issues) > 10:
                            console.print(f"\n[dim]... and {len(issues) - 10} more issues[/dim]")

                    # Add to history
                    execution_time = time.time() - start_time
                    try:
                        history_manager = HistoryManager()
                        history_manager.add_query(
                            query=keywords,
                            product=product,
                            parsed_query=final_query,
                            language=parse_language,
                            method=parse_method,
                            confidence=parse_confidence,
                            results_count=len(issues),
                            execution_time=execution_time
                        )
                        logger.debug(f"Query added to history: {keywords[:50]}...")
                    except Exception as e:
                        logger.warning(f"Failed to add query to history: {e}")

                except Exception as e:
                    progress.stop()
                    console.print(f"[red]❌ Crawl failed: {e}[/red]")
                    logger.exception("Crawl error details:")
                    sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Crawl interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        logger.exception("Error details:")
        sys.exit(1)


@cli.command()
def config():
    """Show current configuration"""

    config_table = Table(title="⚙️  IMS Crawler Configuration")
    config_table.add_column("Setting", style="cyan", no_wrap=True)
    config_table.add_column("Value", style="green")
    config_table.add_column("Status", style="yellow")

    # Check configuration
    checks = [
        ("IMS Base URL", settings.IMS_BASE_URL, bool(settings.IMS_BASE_URL)),
        ("Username", settings.IMS_USERNAME or "[not set]", bool(settings.IMS_USERNAME)),
        ("Password", "***" if settings.IMS_PASSWORD else "[not set]", bool(settings.IMS_PASSWORD)),
        ("Output Directory", str(settings.OUTPUT_DIR), settings.OUTPUT_DIR.exists()),
        ("Attachments Directory", str(settings.ATTACHMENTS_DIR), settings.ATTACHMENTS_DIR.exists()),
        ("Max Results", str(settings.DEFAULT_MAX_RESULTS), True),
        ("Download Attachments", str(settings.DOWNLOAD_ATTACHMENTS), True),
    ]

    for name, value, status in checks:
        status_icon = "✅" if status else "❌"
        config_table.add_row(name, value, status_icon)

    console.print(config_table)

    # Show warnings
    if not all(check[2] for check in checks[:3]):
        console.print()
        console.print("[yellow]⚠️  Warning: Required configuration missing[/yellow]")
        console.print("Please create a .env file (see .env.example)")


@cli.command()
@click.argument('query')
def test_query(query):
    """
    Test IMS search query syntax

    Examples:

    \b
    $ python main.py test-query "Tmax Tibero"
    $ python main.py test-query "connection +error"
    $ python main.py test-query '"system failure" +critical'
    """
    from crawler.search import SearchQueryBuilder

    builder = SearchQueryBuilder()

    console.print(Panel.fit(
        f"[cyan]Query:[/cyan] {query}\n"
        f"[green]Interpretation:[/green] IMS will search using this exact string",
        title="🔍 Search Query Test",
        border_style="cyan"
    ))

    # Explain query syntax
    console.print("\n[yellow]Query Syntax Guide:[/yellow]")
    console.print("• Space-separated = OR search (e.g., 'Tmax Tibero')")
    console.print("• +keyword = AND search (e.g., 'error +critical')")
    console.print('• "exact phrase" = Exact match (e.g., \'"connection timeout"\')')
    console.print("• Combine all (e.g., 'Tmax +error \"system failure\"')")


@cli.command()
@click.option('--limit', '-n', default=20, type=int, help='Number of records to show')
@click.option('--product', '-p', help='Filter by product')
@click.option('--language', '-l', help='Filter by language (en/ko/ja)')
@click.option('--method', '-m', help='Filter by parsing method (rules/llm/direct)')
def history(limit, product, language, method):
    """
    View query history

    Shows recent queries with parsing details and statistics.

    Examples:

    \b
    # Show last 20 queries
    $ python main.py history

    \b
    # Show last 10 queries for Tibero
    $ python main.py history --limit 10 --product "Tibero"

    \b
    # Show Korean queries only
    $ python main.py history --language ko
    """
    manager = HistoryManager()
    records = manager.get_history(limit=limit, product=product, language=language, method=method)

    if not records:
        console.print("[yellow]No query history found[/yellow]")
        return

    table = Table(title=f"📜 Query History (Last {len(records)} queries)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Time", style="cyan", width=16)
    table.add_column("Product", style="green", width=12)
    table.add_column("Query", style="white", width=40)
    table.add_column("Lang", style="yellow", width=4)
    table.add_column("Method", style="magenta", width=6)
    table.add_column("Conf", style="blue", width=5)
    table.add_column("Results", style="green", width=7)

    for idx, record in enumerate(records, 1):
        timestamp = record.timestamp.split('T')[1][:8] if 'T' in record.timestamp else record.timestamp[:8]
        confidence_str = f"{record.confidence:.0%}"

        table.add_row(
            str(idx),
            timestamp,
            record.product[:12],
            record.query[:40],
            record.language.upper(),
            record.method[:6],
            confidence_str,
            str(record.results_count)
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(records)} queries[/dim]")


@cli.command()
@click.option('--add', '-a', type=int, help='Add query from history (index)')
@click.option('--remove', '-r', type=int, help='Remove favorite (index)')
@click.option('--list', '-l', 'list_fav', is_flag=True, help='List all favorites')
def favorites(add, remove, list_fav):
    """
    Manage favorite queries

    Save frequently used queries for quick access.

    Examples:

    \b
    # List all favorites
    $ python main.py favorites --list

    \b
    # Add last query to favorites
    $ python main.py favorites --add -1

    \b
    # Remove favorite by index
    $ python main.py favorites --remove 0
    """
    manager = HistoryManager()

    if add is not None:
        try:
            manager.add_to_favorites(query_index=add)
            console.print(f"[green]✓[/green] Added query #{add} to favorites")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to add: {e}")
        return

    if remove is not None:
        try:
            manager.remove_from_favorites(index=remove)
            console.print(f"[green]✓[/green] Removed favorite #{remove}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to remove: {e}")
        return

    # Default: list favorites
    favs = manager.get_favorites()

    if not favs:
        console.print("[yellow]No favorite queries yet[/yellow]")
        console.print("\n[dim]Tip: Add favorites with: python main.py favorites --add -1[/dim]")
        return

    table = Table(title="⭐ Favorite Queries")
    table.add_column("#", style="dim", width=4)
    table.add_column("Product", style="green", width=12)
    table.add_column("Query", style="white", width=40)
    table.add_column("Parsed", style="cyan", width=40)
    table.add_column("Lang", style="yellow", width=4)

    for idx, fav in enumerate(favs):
        table.add_row(
            str(idx),
            fav.product[:12],
            fav.query[:40],
            fav.parsed_query[:40],
            fav.language.upper()
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(favs)} favorites[/dim]")


@cli.command()
@click.option('--export', '-e', type=click.Path(), help='Export statistics to file')
def stats(export):
    """
    View query statistics and analytics

    Shows aggregate statistics about query usage patterns.

    Examples:

    \b
    # View statistics
    $ python main.py stats

    \b
    # Export to JSON
    $ python main.py stats --export stats.json
    """
    manager = HistoryManager()
    statistics = manager.get_statistics()

    if statistics['total_queries'] == 0:
        console.print("[yellow]No queries in history yet[/yellow]")
        return

    # Overview panel
    overview = f"""[cyan]Total Queries:[/cyan] {statistics['total_queries']}
[cyan]Favorites:[/cyan] {statistics['favorites_count']}
[cyan]Avg Confidence:[/cyan] {statistics['avg_confidence']:.1%}
[cyan]Avg Results:[/cyan] {statistics['avg_results']:.1f}
[cyan]Avg Execution Time:[/cyan] {statistics['avg_execution_time']:.2f}s"""

    console.print(Panel(overview, title="📊 Query Statistics", border_style="cyan"))

    # By Language table
    if statistics['by_language']:
        lang_table = Table(title="Queries by Language")
        lang_table.add_column("Language", style="yellow")
        lang_table.add_column("Count", style="green")
        lang_table.add_column("Percentage", style="cyan")

        for lang, count in sorted(statistics['by_language'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / statistics['total_queries']) * 100
            lang_table.add_row(lang.upper(), str(count), f"{pct:.1f}%")

        console.print(lang_table)

    # By Product table
    if statistics['by_product']:
        product_table = Table(title="Queries by Product")
        product_table.add_column("Product", style="green")
        product_table.add_column("Count", style="green")
        product_table.add_column("Percentage", style="cyan")

        for product, count in sorted(statistics['by_product'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / statistics['total_queries']) * 100
            product_table.add_row(product, str(count), f"{pct:.1f}%")

        console.print(product_table)

    # By Method table
    if statistics['by_method']:
        method_table = Table(title="Queries by Parsing Method")
        method_table.add_column("Method", style="magenta")
        method_table.add_column("Count", style="green")
        method_table.add_column("Percentage", style="cyan")

        for method, count in sorted(statistics['by_method'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / statistics['total_queries']) * 100
            method_table.add_row(method, str(count), f"{pct:.1f}%")

        console.print(method_table)

    # Export if requested
    if export:
        import json
        with open(export, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, indent=2, ensure_ascii=False)
        console.print(f"\n[green]✓[/green] Statistics exported to {export}")


@cli.command()
def build():
    """
    Interactive query builder

    Build queries step-by-step with guided prompts.
    Load from favorites or history for quick access.

    Examples:

    \b
    # Launch interactive builder
    $ python main.py build

    Features:
    - Step-by-step query construction
    - Load from favorites or history
    - Real-time query preview
    - Automatic query execution
    """
    builder = InteractiveQueryBuilder()
    result = builder.run()

    if result.get('from_favorite'):
        console.print("\n[green]✓[/green] Loaded query from favorites")

    # Auto-execute the built query
    console.print("\n[bold cyan]Executing query...[/bold cyan]")

    # Call crawl programmatically
    from click.testing import CliRunner
    runner = CliRunner()

    args = [
        'crawl',
        '-p', result['product'],
        '-k', result['query'],
        '-m', str(result['max_results']),
        '--no-confirm'  # Skip confirmation since we already previewed
    ]

    runner.invoke(cli, args)


@cli.command()
@click.option('--days', '-d', type=int, help='Days for trend analysis (7 or 30)')
@click.option('--export', '-e', type=click.Path(), help='Export report to JSON file')
@click.option('--format', '-f', type=click.Choice(['full', 'summary']), default='full',
              help='Report format (full or summary)')
def analytics(days, export, format):
    """
    View advanced analytics and parsing performance metrics

    Examples:
        python main.py analytics
        python main.py analytics --days 7
        python main.py analytics --export report.json
        python main.py analytics --format summary
    """
    console.print(Panel.fit(
        "[bold cyan]📊 Advanced Analytics Dashboard[/bold cyan]\n"
        "Query patterns, performance metrics, and trends",
        border_style="cyan"
    ))

    # Initialize analytics engine
    history_manager = HistoryManager()
    analytics_engine = AnalyticsEngine(history_manager)

    if not history_manager.history:
        console.print("[yellow]No query history available yet.[/yellow]")
        console.print("[dim]Run some queries first to generate analytics.[/dim]")
        return

    total_queries = len(history_manager.history)
    console.print(f"\n[bold]Total Queries Analyzed:[/bold] [cyan]{total_queries}[/cyan]\n")

    # 1. Performance Metrics
    if format == 'full':
        console.print("[bold green]⚡ Performance Metrics[/bold green]")
        perf = analytics_engine.get_performance_metrics()

        perf_table = Table(show_header=True, header_style="bold cyan")
        perf_table.add_column("Metric", style="white", width=20)
        perf_table.add_column("Value", style="green", width=30)

        perf_table.add_row("Avg Execution Time", f"{perf['execution_time']['avg']:.2f}s")
        perf_table.add_row("Min/Max Time", f"{perf['execution_time']['min']:.2f}s / {perf['execution_time']['max']:.2f}s")
        perf_table.add_row("Median Time", f"{perf['execution_time']['median']:.2f}s")
        perf_table.add_row("Avg Confidence", f"{perf['confidence']['avg']:.1%}")
        perf_table.add_row("High Confidence", f"{perf['confidence']['high_count']} ({perf['confidence']['high_percentage']:.1f}%)")
        perf_table.add_row("Low Confidence", f"{perf['confidence']['low_count']}")
        perf_table.add_row("Avg Results", f"{perf['results']['avg']:.1f}")
        perf_table.add_row("Success Rate", f"{perf['results']['success_rate']:.1f}%")

        console.print(perf_table)
        console.print()

    # 2. Usage Patterns
    console.print("[bold green]📈 Usage Patterns[/bold green]")
    patterns = analytics_engine.get_usage_patterns()

    if patterns:
        pattern_table = Table(show_header=True, header_style="bold cyan")
        pattern_table.add_column("Pattern", style="white", width=20)
        pattern_table.add_column("Details", style="yellow", width=40)

        if 'peak_hour' in patterns and patterns['peak_hour']['count'] > 0:
            pattern_table.add_row(
                "Peak Hour",
                f"{patterns['peak_hour']['time_range']} ({patterns['peak_hour']['count']} queries)"
            )

        if 'peak_day' in patterns and patterns['peak_day']['count'] > 0:
            pattern_table.add_row(
                "Peak Day",
                f"{patterns['peak_day']['day']} ({patterns['peak_day']['count']} queries)"
            )

        if 'activity' in patterns:
            pattern_table.add_row(
                "Activity Rate",
                f"{patterns['activity']['active_days']}/{patterns['activity']['total_days']} days ({patterns['activity']['activity_rate']:.1f}%)"
            )

        if 'popular_products' in patterns and patterns['popular_products']:
            products = ", ".join([f"{p[0]} ({p[1]})" for p in patterns['popular_products'][:3]])
            pattern_table.add_row("Top Products", products)

        if 'popular_languages' in patterns and patterns['popular_languages']:
            langs = ", ".join([f"{l[0]} ({l[1]})" for l in patterns['popular_languages']])
            pattern_table.add_row("Languages", langs)

        console.print(pattern_table)
        console.print()

    # 3. Parsing Accuracy
    if format == 'full':
        console.print("[bold green]🎯 Parsing Accuracy by Method[/bold green]")
        accuracy = analytics_engine.get_parsing_accuracy()

        if accuracy:
            acc_table = Table(show_header=True, header_style="bold cyan")
            acc_table.add_column("Method", style="white", width=12)
            acc_table.add_column("Count", style="cyan", width=10)
            acc_table.add_column("Avg Confidence", style="green", width=15)
            acc_table.add_column("Avg Results", style="yellow", width=15)
            acc_table.add_column("Success Rate", style="magenta", width=15)

            for method, metrics in accuracy.items():
                acc_table.add_row(
                    method,
                    str(metrics['count']),
                    f"{metrics['avg_confidence']:.1%}",
                    f"{metrics['avg_results']:.1f}",
                    f"{metrics['success_rate']:.1f}%"
                )

            console.print(acc_table)
            console.print()

    # 4. Query Complexity Analysis
    if format == 'full':
        console.print("[bold green]🧩 Query Complexity Analysis[/bold green]")
        complexity = analytics_engine.get_query_complexity_analysis()

        if complexity:
            comp_table = Table(show_header=True, header_style="bold cyan")
            comp_table.add_column("Complexity", style="white", width=15)
            comp_table.add_column("Count", style="cyan", width=10)
            comp_table.add_column("Percentage", style="green", width=15)
            comp_table.add_column("Avg Exec Time", style="yellow", width=15)

            for level in ['simple', 'medium', 'complex']:
                if level in complexity:
                    comp_table.add_row(
                        level.capitalize(),
                        str(complexity[level]['count']),
                        f"{complexity[level]['percentage']:.1f}%",
                        f"{complexity[level]['avg_exec_time']:.2f}s"
                    )

            console.print(comp_table)
            console.print()

    # 5. Trend Analysis
    trend_days = days or 7
    console.print(f"[bold green]📊 Trend Analysis ({trend_days} days)[/bold green]")
    trends = analytics_engine.get_trend_analysis(days=trend_days)

    if trends and trends.get('total_queries', 0) > 0:
        trend_table = Table(show_header=True, header_style="bold cyan")
        trend_table.add_column("Metric", style="white", width=20)
        trend_table.add_column("Value", style="yellow", width=30)

        trend_table.add_row("Period", f"{trends['period_days']} days")
        trend_table.add_row("Total Queries", str(trends['total_queries']))
        trend_table.add_row("Avg per Day", f"{trends['avg_per_day']:.1f}")
        trend_table.add_row("Growth Rate", f"{trends['growth_rate']:+.1f}%")

        console.print(trend_table)
        console.print()

        # Daily stats
        if format == 'full' and 'daily_stats' in trends and trends['daily_stats']:
            console.print("[bold]Daily Breakdown:[/bold]")
            daily_table = Table(show_header=True, header_style="bold cyan")
            daily_table.add_column("Date", style="white", width=12)
            daily_table.add_column("Queries", style="cyan", width=10)
            daily_table.add_column("Avg Confidence", style="green", width=15)
            daily_table.add_column("Avg Results", style="yellow", width=15)

            for date, stats in sorted(trends['daily_stats'].items())[-7:]:  # Last 7 days
                daily_table.add_row(
                    date,
                    str(stats['count']),
                    f"{stats['avg_confidence']:.1%}",
                    f"{stats['avg_results']:.1f}"
                )

            console.print(daily_table)
            console.print()
    else:
        console.print(f"[yellow]No queries in the last {trend_days} days.[/yellow]\n")

    # 6. Export Report
    if export:
        console.print(f"[bold]Exporting report to:[/bold] [cyan]{export}[/cyan]")
        report = analytics_engine.generate_report(output_file=Path(export))
        console.print(f"[green]✓[/green] Report exported successfully")
        console.print(f"[dim]Report contains: {len(report)} sections[/dim]")


@cli.command()
@click.option(
    '--query', '-q',
    required=True,
    help='Search query used for crawling (for report context)'
)
@click.option(
    '--product', '-p',
    default='OpenFrame',
    help='Product name (default: OpenFrame)'
)
@click.option(
    '--input-dir', '-i',
    default=None,
    type=click.Path(exists=True),
    help='Directory containing issue JSON files (default: latest crawl session for product)'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output markdown file (default: auto-generated based on query)'
)
@click.option(
    '--language', '-l',
    default='ko',
    type=click.Choice(['ko', 'ja', 'en']),
    help='Report language (default: ko)'
)
@click.option(
    '--use-llm/--no-llm',
    default=False,
    help='Use local LLM for enhanced analysis (requires Ollama, default: no)'
)
@click.option(
    '--llm-model',
    default='gemma:2b',
    help='LLM model to use (default: gemma:2b)'
)
def generate_report(query, product, input_dir, output, language, use_llm, llm_model):
    """
    📝 Generate comprehensive markdown report from crawled issue data

    Analyzes crawled JSON files and generates structured markdown reports
    with executive summary, technical analysis, and recommendations.

    Works offline using templates, or can be enhanced with local LLM.

    Examples:

        # Basic report (template-only, offline)
        python main.py generate-report -q "SVC99 DYNALLOC" -p "OpenFrame"

        # LLM-enhanced report (requires Ollama)
        python main.py generate-report -q "connection timeout" --use-llm

        # Custom output and language
        python main.py generate-report -q "error" -o custom_report.md -l en
    """
    import json
    import time
    from datetime import datetime

    console.print(Panel(
        "[bold cyan]IMS Report Generator[/bold cyan]\n"
        "Autonomous report generation from crawled issue data",
        title="📝 Report Generator",
        border_style="cyan"
    ))

    # Initialize LLM client if requested
    llm_client = None
    if use_llm:
        console.print("[yellow]⚙[/yellow]  Initializing LLM client...")
        try:
            if llm_model != 'gemma:2b':
                from crawler.llm_client import OllamaClient, LLMConfig
                config = LLMConfig(model=llm_model)
                llm_client = OllamaClient(config=config)
            else:
                llm_client = get_default_llm_client()

            if llm_client and llm_client.available:
                console.print(f"[green]✓[/green] LLM client initialized: {llm_client.config.model}")
            else:
                console.print("[yellow]⚠[/yellow]  LLM not available, using template-only mode")
                console.print("[dim]To use LLM: ollama serve && ollama pull gemma:2b[/dim]")
                llm_client = None
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow]  LLM initialization failed: {e}")
            console.print("[yellow]⚙[/yellow]  Falling back to template-only mode")
            llm_client = None
    else:
        console.print("[cyan]ℹ[/cyan]  Using template-based report generation (offline mode)")

    # Initialize report generator
    generator = ReportGenerator(llm_client=llm_client)

    # Auto-detect latest session folder if input_dir not specified
    if input_dir is None:
        console.print(f"[yellow]🔍[/yellow] Auto-detecting latest crawl session for product: [cyan]{product}[/cyan]")

        base_dir = Path("data/crawl_sessions")
        latest_folder = get_latest_crawl_folder(base_dir, product=product)

        if latest_folder is None:
            console.print(f"[red]✗[/red] No crawl sessions found for product '{product}'")
            console.print("[yellow]Tip:[/yellow] Run a crawl first: python main.py crawl -p \"{product}\" -k 'keywords'")
            sys.exit(1)

        input_dir = str(latest_folder)
        console.print(f"[green]✓[/green] Using latest session: [cyan]{latest_folder.name}[/cyan]")

    # Load issues from directory
    console.print(f"[yellow]📂[/yellow] Loading issues from: [cyan]{input_dir}[/cyan]")
    input_path = Path(input_dir)

    issues = generator.load_issues(input_path)

    if not issues:
        console.print(f"[red]✗[/red] No issue files found in {input_dir}")
        console.print("[yellow]Tip:[/yellow] Run a crawl first: python main.py crawl -p Product -k 'keywords'")
        sys.exit(1)

    console.print(f"[green]✓[/green] Loaded {len(issues)} issue(s)")

    # Generate output filename if not specified
    if not output:
        # Create filename from query
        safe_query = "".join(c if c.isalnum() else '_' for c in query)
        timestamp = datetime.now().strftime("%Y%m%d")
        output = f"{safe_query}_{timestamp}_report.md"

    output_path = Path(output)

    # Generate report
    console.print(f"[yellow]⚙[/yellow]  Generating report...")
    console.print(f"[dim]Query: {query}[/dim]")
    console.print(f"[dim]Product: {product}[/dim]")
    console.print(f"[dim]Language: {language}[/dim]")
    console.print(f"[dim]Mode: {'LLM-enhanced' if llm_client else 'Template-only'}[/dim]")

    start_time = time.time()

    try:
        report_content = generator.generate_report(
            query=query,
            product=product,
            issues=issues,
            output_file=output_path,
            language=language
        )

        elapsed = time.time() - start_time

        # Success
        console.print()
        console.print(Panel(
            f"[green]✓[/green] Report generated successfully!\n\n"
            f"[bold]Output:[/bold] [cyan]{output_path}[/cyan]\n"
            f"[bold]Size:[/bold] {len(report_content)} characters\n"
            f"[bold]Issues analyzed:[/bold] {len(issues)}\n"
            f"[bold]Generation time:[/bold] {elapsed:.2f}s",
            title="✅ Success",
            border_style="green"
        ))

        # Show preview
        console.print("\n[bold]Report Preview:[/bold]")
        preview_lines = report_content.split('\n')[:20]
        console.print("[dim]" + "\n".join(preview_lines) + "[/dim]")
        if len(report_content.split('\n')) > 20:
            console.print("[dim]...[/dim]")

        console.print(f"\n[cyan]→[/cyan] View full report: [bold]{output_path}[/bold]")

    except Exception as e:
        console.print(f"\n[red]✗[/red] Report generation failed: {e}")
        logger.exception("Report generation error")
        sys.exit(1)


if __name__ == '__main__':
    cli()
