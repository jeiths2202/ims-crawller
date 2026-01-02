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

    # Display crawl configuration
    config_table = Table(title="🔧 Crawl Configuration", show_header=False)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Product", product)
    config_table.add_row("Search Query", final_query)
    config_table.add_row("Max Results", str(max_results))
    config_table.add_row("Output Dir", output_dir)
    config_table.add_row("Headless", "Yes" if headless else "No")
    config_table.add_row("Crawl Related Issues", "Yes" if crawl_related else "No")
    if crawl_related:
        config_table.add_row("Max Depth", str(max_depth))

    console.print(config_table)
    console.print()

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize scraper
        console.print("[yellow]🚀 Initializing crawler...[/yellow]")

        with IMSScraper(
            base_url=settings.IMS_BASE_URL,
            username=settings.IMS_USERNAME,
            password=settings.IMS_PASSWORD,
            output_dir=output_path,
            attachments_dir=settings.ATTACHMENTS_DIR,
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
                    result_msg += f"\n[cyan]📁 Output directory: {output_dir}[/cyan]"

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


if __name__ == '__main__':
    cli()
