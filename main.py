"""
IMS Crawler - Main CLI Interface
Command-line tool for crawling IMS issues
"""
import sys
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
    help='Search keywords using IMS syntax (e.g., "connection +error")'
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
def crawl(product, keywords, max_results, output_dir, headless):
    """
    Crawl IMS issues based on search criteria

    Examples:

    \b
    # Crawl Tibero connection errors
    $ python main.py crawl -p "Tibero" -k "connection +error" -m 50

    \b
    # Crawl with exact phrase search
    $ python main.py crawl -p "JEUS" -k '"out of memory"' -m 100

    \b
    # Crawl with complex query (OR + AND + exact phrase)
    $ python main.py crawl -p "Tibero" -k 'timeout crash +error +"system failure"'
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

    # Display crawl configuration
    config_table = Table(title="🔧 Crawl Configuration", show_header=False)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Product", product)
    config_table.add_row("Keywords", keywords)
    config_table.add_row("Max Results", str(max_results))
    config_table.add_row("Output Dir", output_dir)
    config_table.add_row("Headless", "Yes" if headless else "No")

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
            headless=headless
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
                        keywords=keywords,
                        max_results=max_results
                    )

                    progress.update(task, completed=len(issues))

                    # Display results
                    console.print()
                    console.print(Panel.fit(
                        f"[green]✅ Successfully crawled {len(issues)} issues[/green]\n"
                        f"[cyan]📁 Output directory: {output_dir}[/cyan]",
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
