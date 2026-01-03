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
@click.option(
    '--user-id',
    type=int,
    help='User ID for database operations (if not specified, uses default from username)'
)
@click.option(
    '--use-database/--no-database',
    default=settings.USE_DATABASE,
    help=f'Save crawl data to PostgreSQL database (default: {"enabled" if settings.USE_DATABASE else "disabled"})'
)
def crawl(product, keywords, max_results, output_dir, headless, crawl_related, max_depth, no_confirm, no_llm, user_id, use_database):
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

    # Determine user_id for database operations
    db_user_id = user_id
    if use_database and not db_user_id:
        # Try to look up user by username
        try:
            from database import get_session, User
            with get_session() as session:
                user = session.query(User).filter_by(username=settings.IMS_USERNAME).first()
                if user:
                    db_user_id = user.user_id
                    console.print(f"[dim]Using database user_id={db_user_id} for username '{settings.IMS_USERNAME}'[/dim]")
                else:
                    console.print(f"[yellow]⚠[/yellow] User '{settings.IMS_USERNAME}' not found in database, using default user_id=2")
                    db_user_id = 2  # Default to yijae.shin user
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Failed to lookup user_id: {e}")
            console.print("[yellow]⚠[/yellow] Continuing without database")
            use_database = False

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
    config_table.add_row("Database", "Enabled" if use_database else "Disabled")
    if use_database and db_user_id:
        config_table.add_row("Database User ID", str(db_user_id))

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
            cookie_file=settings.COOKIE_FILE,
            user_id=db_user_id,
            use_database=use_database
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


@cli.command()
@click.option(
    '--query', '-q',
    required=True,
    help='Search query (Korean/Japanese/English supported)'
)
@click.option(
    '--session', '-s',
    default=None,
    help='Session folder name or path (auto-detect latest if not specified)'
)
@click.option(
    '--product', '-p',
    default=None,
    help='Filter by product when auto-detecting session'
)
@click.option(
    '--top-k', '-k',
    default=10,
    type=int,
    help='Number of results to display (default: 10)'
)
@click.option(
    '--show-scores',
    is_flag=True,
    help='Show detailed score breakdown (BM25 + Semantic)'
)
@click.option(
    '--threshold',
    default=0.0,
    type=float,
    help='Minimum similarity score (0.0-1.0, default: 0.0)'
)
def search(query, session, product, top_k, show_scores, threshold):
    """
    🔍 Search for relevant comments in crawled IMS issues

    Uses hybrid search (BM25 + Semantic) optimized for Korean/Japanese/English.

    Examples:

        # Search in latest session
        python main.py search -q "TPETIME 에러 원인"

        # Search in specific session
        python main.py search -q "timeout error" -s OpenFrame_TPETIME_20260103_045204

        # Filter by product and show more results
        python main.py search -q "batch job failure" -p OpenFrame -k 20

        # Show score breakdown
        python main.py search -q "connection timeout" --show-scores
    """
    import json
    import time

    console.print(Panel(
        "[bold cyan]Hybrid Search Engine[/bold cyan]\n"
        "BM25 (30%) + Semantic (70%) with CJK optimization",
        title="🔍 IMS Issue Search",
        border_style="cyan"
    ))

    # Check if dependencies are installed
    try:
        from examples.production_search import ProductionHybridSearch
    except ImportError as e:
        console.print(f"[red]✗[/red] Search dependencies not installed")
        console.print(f"[yellow]Error:[/yellow] {e}")
        console.print("\n[cyan]Install with:[/cyan]")
        console.print("  pip install sentence-transformers rank-bm25")
        sys.exit(1)

    # Initialize search engine
    console.print("[yellow]⚙[/yellow]  Initializing hybrid search engine...")
    try:
        searcher = ProductionHybridSearch()
        console.print("[green]✓[/green] Search engine initialized")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to initialize search engine: {e}")
        sys.exit(1)

    # Determine session folder
    if session:
        # Use specified session
        session_path = Path(session)
        if not session_path.is_absolute():
            # Treat as session folder name
            session_path = Path("data/crawl_sessions") / session

        if not session_path.exists():
            console.print(f"[red]✗[/red] Session folder not found: {session_path}")
            sys.exit(1)

        console.print(f"[cyan]📁[/cyan] Session: [bold]{session_path.name}[/bold]")

    else:
        # Auto-detect latest session
        console.print("[yellow]🔍[/yellow] Auto-detecting latest crawl session...")
        if product:
            console.print(f"[dim]Filtering by product: {product}[/dim]")

        base_dir = Path("data/crawl_sessions")
        latest_folder = get_latest_crawl_folder(base_dir, product=product)

        if latest_folder is None:
            console.print(f"[red]✗[/red] No crawl sessions found")
            if product:
                console.print(f"[yellow]Tip:[/yellow] Run a crawl first: python main.py crawl -p \"{product}\" -k 'keywords'")
            else:
                console.print("[yellow]Tip:[/yellow] Run a crawl first: python main.py crawl -p Product -k 'keywords'")
            sys.exit(1)

        session_path = latest_folder
        console.print(f"[green]✓[/green] Using latest session: [cyan]{session_path.name}[/cyan]")

    # Perform search
    console.print(f"\n[bold]Query:[/bold] [cyan]{query}[/cyan]")
    console.print(f"[dim]Searching across all issues in session...[/dim]\n")

    start_time = time.time()

    try:
        results = searcher.search_session_folder(
            session_folder_path=str(session_path),
            query=query,
            overall_top_k=top_k
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Search failed: {e}")
        logger.exception("Search error")
        sys.exit(1)

    elapsed = time.time() - start_time

    # Display results
    if not results:
        console.print("[yellow]⚠[/yellow]  No results found")
        console.print(f"[dim]Try different keywords or lower the threshold (current: {threshold})[/dim]")
        return

    # Filter by threshold
    filtered_results = [r for r in results if r['score'] >= threshold]

    if not filtered_results:
        console.print(f"[yellow]⚠[/yellow]  No results above threshold {threshold:.2f}")
        console.print(f"[dim]Found {len(results)} results below threshold[/dim]")
        return

    # Create results table
    table = Table(title=f"🔍 Search Results ({len(filtered_results)} found)", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Issue ID", style="cyan", width=8)
    table.add_column("Title", style="bold", width=40)
    table.add_column("Product", style="green", width=15)
    table.add_column("Score", style="magenta", width=6)

    for i, result in enumerate(filtered_results, 1):
        table.add_row(
            str(i),
            str(result['issue_id']),
            result['title'][:37] + "..." if len(result['title']) > 40 else result['title'],
            result['product'][:12] + "..." if len(result['product']) > 15 else result['product'],
            f"{result['score']:.3f}"
        )

    console.print(table)

    # Display detailed results
    console.print(f"\n[bold]Top {min(5, len(filtered_results))} Results (Detailed):[/bold]\n")

    for i, result in enumerate(filtered_results[:5], 1):
        console.print(f"[bold cyan][{i}] Issue {result['issue_id']}[/bold cyan]")
        console.print(f"    [bold]Title:[/bold] {result['title']}")
        console.print(f"    [bold]Product:[/bold] {result['product']} | [bold]Status:[/bold] {result['status']}")
        console.print(f"    [bold]Score:[/bold] [magenta]{result['score']:.3f}[/magenta]")

        if show_scores:
            # Show score breakdown (would need to modify search to return this)
            console.print(f"    [dim]  (Hybrid: BM25 30% + Semantic 70%)[/dim]")

        console.print(f"    [bold]Comment:[/bold]")
        comment_content = result['comment']['content']
        preview = comment_content[:200] + "..." if len(comment_content) > 200 else comment_content
        console.print(f"    [dim]{preview}[/dim]")

        console.print(f"    [dim]Author: {result['comment'].get('author', 'Unknown')} | "
                     f"Date: {result['comment'].get('created_date', 'N/A')}[/dim]")
        console.print()

    # Summary
    console.print(Panel(
        f"[green]✓[/green] Search completed\n\n"
        f"[bold]Results:[/bold] {len(filtered_results)} issues\n"
        f"[bold]Search time:[/bold] {elapsed:.2f}s\n"
        f"[bold]Method:[/bold] Hybrid (BM25 + Semantic)\n"
        f"[bold]Session:[/bold] {session_path.name}",
        title="✅ Search Summary",
        border_style="green"
    ))

    # Show tip for viewing full content
    if filtered_results:
        first_result = filtered_results[0]
        console.print(f"\n[cyan]💡 Tip:[/cyan] View full issue: [bold]{first_result['file_path']}[/bold]")


@cli.group()
def db():
    """
    Database management commands

    Manage and query the PostgreSQL database for crawl history,
    statistics, and data exploration.
    """
    pass


@db.command()
@click.option(
    '--user-id',
    type=int,
    help='User ID (default: current user from .env)'
)
def stats(user_id):
    """
    Display user statistics and database summary

    Shows comprehensive statistics including:
    - Total sessions and issues crawled
    - Average crawl performance metrics
    - Database storage information
    - Recent activity summary

    Examples:

    \b
    # Show stats for current user
    $ python main.py db stats

    \b
    # Show stats for specific user
    $ python main.py db stats --user-id 2
    """
    from database import get_session, User, CrawlSession, Issue
    from sqlalchemy import func, text

    # Determine user_id
    if not user_id:
        try:
            with get_session() as session:
                user = session.query(User).filter_by(username=settings.IMS_USERNAME).first()
                if user:
                    user_id = user.user_id
                else:
                    console.print(f"[yellow]⚠[/yellow] User '{settings.IMS_USERNAME}' not found, using user_id=2")
                    user_id = 2
        except Exception as e:
            console.print(f"[red]✗[/red] Database connection failed: {e}")
            return

    try:
        with get_session(user_id=user_id) as session:
            # Get user info
            user = session.get(User, user_id)
            if not user:
                console.print(f"[red]✗[/red] User ID {user_id} not found")
                return

            console.print()
            console.print(Panel(
                f"[bold cyan]User:[/bold cyan] {user.username}\n"
                f"[bold cyan]Email:[/bold cyan] {user.email or 'N/A'}\n"
                f"[bold cyan]Role:[/bold cyan] {user.role or 'user'}",
                title="👤 User Information",
                border_style="cyan"
            ))
            console.print()

            # Session statistics
            session_stats = session.query(
                func.count(CrawlSession.session_id).label('total_sessions'),
                func.sum(CrawlSession.issues_crawled).label('total_issues'),
                func.sum(CrawlSession.attachments_downloaded).label('total_attachments'),
                func.avg(CrawlSession.duration_seconds).label('avg_duration'),
                func.avg(CrawlSession.avg_issue_time_ms).label('avg_issue_time')
            ).filter(CrawlSession.user_id == user_id).first()

            # Recent sessions
            recent = session.query(CrawlSession).filter(
                CrawlSession.user_id == user_id
            ).order_by(CrawlSession.started_at.desc()).limit(5).all()

            # Status breakdown
            status_counts = session.query(
                CrawlSession.status,
                func.count(CrawlSession.session_id).label('count')
            ).filter(CrawlSession.user_id == user_id).group_by(CrawlSession.status).all()

            # Display statistics
            stats_table = Table(title="📊 Crawl Statistics", show_header=False)
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="green")

            stats_table.add_row("Total Sessions", str(session_stats.total_sessions or 0))
            stats_table.add_row("Total Issues Crawled", str(session_stats.total_issues or 0))
            stats_table.add_row("Total Attachments", str(session_stats.total_attachments or 0))

            if session_stats.avg_duration:
                stats_table.add_row("Avg Session Duration", f"{session_stats.avg_duration:.1f} seconds")
            if session_stats.avg_issue_time:
                stats_table.add_row("Avg Issue Crawl Time", f"{session_stats.avg_issue_time:.0f} ms")

            console.print(stats_table)
            console.print()

            # Status breakdown
            if status_counts:
                status_table = Table(title="📈 Session Status")
                status_table.add_column("Status", style="cyan")
                status_table.add_column("Count", style="green", justify="right")

                for status, count in status_counts:
                    status_style = {
                        'completed': 'green',
                        'running': 'yellow',
                        'failed': 'red'
                    }.get(status, 'white')
                    status_table.add_row(f"[{status_style}]{status}[/{status_style}]", str(count))

                console.print(status_table)
                console.print()

            # Recent activity
            if recent:
                recent_table = Table(title="🕒 Recent Sessions")
                recent_table.add_column("ID", style="cyan", width=4)
                recent_table.add_column("Date", style="white", width=19)
                recent_table.add_column("Product", style="yellow", width=12)
                recent_table.add_column("Query", style="white", width=30)
                recent_table.add_column("Issues", style="green", justify="right", width=6)
                recent_table.add_column("Status", style="white", width=10)

                for sess in recent:
                    status_style = {
                        'completed': 'green',
                        'running': 'yellow',
                        'failed': 'red'
                    }.get(sess.status, 'white')

                    query_preview = sess.original_query[:27] + "..." if len(sess.original_query) > 30 else sess.original_query

                    recent_table.add_row(
                        str(sess.session_id),
                        sess.started_at.strftime('%Y-%m-%d %H:%M:%S') if sess.started_at else 'N/A',
                        sess.product[:12] if sess.product else 'N/A',
                        query_preview,
                        str(sess.issues_crawled or 0),
                        f"[{status_style}]{sess.status}[/{status_style}]"
                    )

                console.print(recent_table)
                console.print()

            # Database size info
            try:
                db_size = session.execute(text(
                    "SELECT pg_size_pretty(pg_database_size('ims_crawler')) as size"
                )).fetchone()

                console.print(f"[dim]Database size: {db_size[0]}[/dim]")
            except:
                pass

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to retrieve statistics: {e}")
        import traceback
        traceback.print_exc()


@db.command()
@click.option(
    '--user-id',
    type=int,
    help='User ID (default: current user from .env)'
)
@click.option(
    '--limit',
    type=int,
    default=20,
    help='Number of sessions to show (default: 20)'
)
@click.option(
    '--product',
    help='Filter by product name'
)
@click.option(
    '--status',
    type=click.Choice(['completed', 'running', 'failed']),
    help='Filter by status'
)
@click.option(
    '--details/--no-details',
    default=False,
    help='Show detailed information for each session'
)
def history(user_id, limit, product, status, details):
    """
    Show crawl session history

    Display a list of past crawl sessions with filters and options
    for detailed information.

    Examples:

    \b
    # Show recent 20 sessions
    $ python main.py db history

    \b
    # Show last 50 sessions
    $ python main.py db history --limit 50

    \b
    # Show only completed OpenFrame sessions
    $ python main.py db history --product OpenFrame --status completed

    \b
    # Show detailed information
    $ python main.py db history --limit 10 --details
    """
    from database import get_session, User, CrawlSession, SessionIssue, Issue
    from sqlalchemy import func

    # Determine user_id
    if not user_id:
        try:
            with get_session() as session:
                user = session.query(User).filter_by(username=settings.IMS_USERNAME).first()
                if user:
                    user_id = user.user_id
                else:
                    console.print(f"[yellow]⚠[/yellow] User '{settings.IMS_USERNAME}' not found, using user_id=2")
                    user_id = 2
        except Exception as e:
            console.print(f"[red]✗[/red] Database connection failed: {e}")
            return

    try:
        with get_session(user_id=user_id) as session:
            # Build query
            query = session.query(CrawlSession).filter(CrawlSession.user_id == user_id)

            # Apply filters
            if product:
                query = query.filter(CrawlSession.product.ilike(f'%{product}%'))
            if status:
                query = query.filter(CrawlSession.status == status)

            # Order and limit
            query = query.order_by(CrawlSession.started_at.desc()).limit(limit)

            sessions = query.all()

            if not sessions:
                console.print("[yellow]No sessions found matching criteria[/yellow]")
                return

            console.print()

            if not details:
                # Summary table
                table = Table(title=f"📚 Session History ({len(sessions)} sessions)")
                table.add_column("ID", style="cyan", width=4)
                table.add_column("Started", style="white", width=19)
                table.add_column("Product", style="yellow", width=12)
                table.add_column("Query", style="white", width=35)
                table.add_column("Found", style="blue", justify="right", width=6)
                table.add_column("Crawled", style="green", justify="right", width=7)
                table.add_column("Duration", style="magenta", justify="right", width=8)
                table.add_column("Status", style="white", width=10)

                for sess in sessions:
                    status_style = {
                        'completed': 'green',
                        'running': 'yellow',
                        'failed': 'red'
                    }.get(sess.status, 'white')

                    query_preview = sess.original_query[:32] + "..." if len(sess.original_query) > 35 else sess.original_query
                    duration_str = f"{sess.duration_seconds}s" if sess.duration_seconds else "N/A"

                    table.add_row(
                        str(sess.session_id),
                        sess.started_at.strftime('%Y-%m-%d %H:%M:%S') if sess.started_at else 'N/A',
                        sess.product[:12] if sess.product else 'N/A',
                        query_preview,
                        str(sess.total_issues_found or 0),
                        str(sess.issues_crawled or 0),
                        duration_str,
                        f"[{status_style}]{sess.status}[/{status_style}]"
                    )

                console.print(table)
            else:
                # Detailed view
                for i, sess in enumerate(sessions, 1):
                    status_style = {
                        'completed': 'green',
                        'running': 'yellow',
                        'failed': 'red'
                    }.get(sess.status, 'white')

                    # Get issues for this session
                    issue_count = session.query(func.count(SessionIssue.issue_pk)).filter(
                        SessionIssue.session_id == sess.session_id
                    ).scalar()

                    details_text = f"[bold]Session ID:[/bold] {sess.session_id}\n"
                    details_text += f"[bold]UUID:[/bold] {sess.session_uuid}\n"
                    details_text += f"[bold]Product:[/bold] {sess.product}\n"
                    details_text += f"[bold]Query:[/bold] {sess.original_query}\n"
                    details_text += f"[bold]Parsed Query:[/bold] {sess.parsed_query}\n"
                    details_text += f"[bold]Status:[/bold] [{status_style}]{sess.status}[/{status_style}]\n\n"

                    details_text += f"[bold cyan]Results:[/bold cyan]\n"
                    details_text += f"  Issues Found: {sess.total_issues_found or 0}\n"
                    details_text += f"  Issues Crawled: {sess.issues_crawled or 0}\n"
                    details_text += f"  Attachments: {sess.attachments_downloaded or 0}\n"
                    details_text += f"  Failed: {sess.failed_issues or 0}\n\n"

                    if sess.search_time_ms:
                        details_text += f"[bold magenta]Performance:[/bold magenta]\n"
                        details_text += f"  Search Time: {sess.search_time_ms}ms\n"
                        details_text += f"  Crawl Time: {sess.crawl_time_ms or 'N/A'}ms\n"
                        details_text += f"  Avg Issue Time: {sess.avg_issue_time_ms or 'N/A'}ms\n"
                        details_text += f"  Total Duration: {sess.duration_seconds or 'N/A'}s\n"
                        details_text += f"  Workers: {sess.parallel_workers or 1}\n\n"

                    details_text += f"[bold yellow]Timeline:[/bold yellow]\n"
                    details_text += f"  Started: {sess.started_at.strftime('%Y-%m-%d %H:%M:%S') if sess.started_at else 'N/A'}\n"
                    details_text += f"  Completed: {sess.completed_at.strftime('%Y-%m-%d %H:%M:%S') if sess.completed_at else 'N/A'}"

                    console.print(Panel(
                        details_text,
                        title=f"📋 Session {i}/{len(sessions)}",
                        border_style=status_style
                    ))
                    console.print()

            # Summary
            total_issues = sum(s.issues_crawled or 0 for s in sessions)
            console.print(f"[dim]Total issues crawled: {total_issues}[/dim]")
            console.print()

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to retrieve history: {e}")
        import traceback
        traceback.print_exc()


@db.command()
@click.argument('session_id', type=int)
def session(session_id):
    """
    Show detailed information for a specific session

    Display complete information including all issues crawled,
    errors encountered, and performance metrics.

    Examples:

    \b
    # Show session details
    $ python main.py db session 7
    """
    from database import get_session, CrawlSession, SessionIssue, Issue, SessionError

    try:
        with get_session() as session:
            # Get session
            crawl_session = session.get(CrawlSession, session_id)

            if not crawl_session:
                console.print(f"[red]✗[/red] Session {session_id} not found")
                return

            status_style = {
                'completed': 'green',
                'running': 'yellow',
                'failed': 'red'
            }.get(crawl_session.status, 'white')

            # Session info
            console.print()
            session_info = f"[bold]UUID:[/bold] {crawl_session.session_uuid}\n"
            session_info += f"[bold]User ID:[/bold] {crawl_session.user_id}\n"
            session_info += f"[bold]Product:[/bold] {crawl_session.product}\n"
            session_info += f"[bold]Status:[/bold] [{status_style}]{crawl_session.status}[/{status_style}]\n\n"

            session_info += f"[bold cyan]Query:[/bold cyan]\n"
            session_info += f"  Original: {crawl_session.original_query}\n"
            session_info += f"  Parsed: {crawl_session.parsed_query}\n"
            session_info += f"  Language: {crawl_session.query_language}\n\n"

            session_info += f"[bold green]Results:[/bold green]\n"
            session_info += f"  Found: {crawl_session.total_issues_found or 0}\n"
            session_info += f"  Crawled: {crawl_session.issues_crawled or 0}\n"
            session_info += f"  Attachments: {crawl_session.attachments_downloaded or 0}\n"
            session_info += f"  Failed: {crawl_session.failed_issues or 0}\n\n"

            if crawl_session.search_time_ms:
                session_info += f"[bold magenta]Performance:[/bold magenta]\n"
                session_info += f"  Search: {crawl_session.search_time_ms}ms\n"
                session_info += f"  Crawl: {crawl_session.crawl_time_ms or 'N/A'}ms\n"
                session_info += f"  Avg/Issue: {crawl_session.avg_issue_time_ms or 'N/A'}ms\n"
                session_info += f"  Duration: {crawl_session.duration_seconds or 'N/A'}s\n"
                session_info += f"  Workers: {crawl_session.parallel_workers or 1}\n\n"

            session_info += f"[bold yellow]Timeline:[/bold yellow]\n"
            session_info += f"  Started: {crawl_session.started_at.strftime('%Y-%m-%d %H:%M:%S') if crawl_session.started_at else 'N/A'}\n"
            session_info += f"  Completed: {crawl_session.completed_at.strftime('%Y-%m-%d %H:%M:%S') if crawl_session.completed_at else 'N/A'}"

            console.print(Panel(
                session_info,
                title=f"📋 Session {session_id}",
                border_style=status_style
            ))
            console.print()

            # Get issues
            session_issues = session.query(SessionIssue, Issue).join(
                Issue, SessionIssue.issue_pk == Issue.issue_pk
            ).filter(
                SessionIssue.session_id == session_id
            ).order_by(SessionIssue.crawl_order).all()

            if session_issues:
                issues_table = Table(title=f"🔍 Issues ({len(session_issues)})")
                issues_table.add_column("#", style="cyan", width=3)
                issues_table.add_column("Issue ID", style="yellow", width=10)
                issues_table.add_column("Title", style="white", width=60)
                issues_table.add_column("Time", style="magenta", justify="right", width=8)

                for si, issue in session_issues:
                    title_preview = issue.title[:57] + "..." if len(issue.title) > 60 else issue.title
                    time_str = f"{si.crawl_duration_ms}ms" if si.crawl_duration_ms else "N/A"

                    issues_table.add_row(
                        str(si.crawl_order) if si.crawl_order else "N/A",
                        issue.issue_id,
                        title_preview,
                        time_str
                    )

                console.print(issues_table)
                console.print()

            # Get errors
            errors = session.query(SessionError).filter(
                SessionError.session_id == session_id
            ).order_by(SessionError.occurred_at).all()

            if errors:
                errors_table = Table(title=f"⚠️  Errors ({len(errors)})")
                errors_table.add_column("Time", style="white", width=19)
                errors_table.add_column("Type", style="yellow", width=20)
                errors_table.add_column("Severity", style="red", width=10)
                errors_table.add_column("Message", style="white", width=50)

                for error in errors:
                    severity_style = {
                        'error': 'red',
                        'warning': 'yellow',
                        'info': 'blue'
                    }.get(error.severity, 'white')

                    msg_preview = error.error_message[:47] + "..." if len(error.error_message) > 50 else error.error_message

                    errors_table.add_row(
                        error.occurred_at.strftime('%Y-%m-%d %H:%M:%S') if error.occurred_at else 'N/A',
                        error.error_type,
                        f"[{severity_style}]{error.severity}[/{severity_style}]",
                        msg_preview
                    )

                console.print(errors_table)
                console.print()

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to retrieve session: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    cli()
