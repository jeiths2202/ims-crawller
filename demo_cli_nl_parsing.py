"""
CLI Natural Language Parsing Demo

Demonstrates the natural language parsing feature integrated into main.py
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from crawler.nl_parser import NaturalLanguageParser, is_ims_syntax

console = Console()


def demo_parsing_workflow():
    """Demonstrate the complete parsing workflow"""

    console.print(Panel.fit(
        "[bold cyan]Natural Language Query Parsing Demo[/bold cyan]\n"
        "Simulating the main.py CLI workflow",
        border_style="cyan"
    ))
    console.print()

    # Demo queries
    queries = [
        ("IMS Syntax (Passthrough)", "+error +crash"),
        ("Natural Language AND", "find error and crash"),
        ("Natural Language OR", "show connection or timeout"),
        ("Exact Phrase", "find 'out of memory'"),
        ("Complex Query", "find database error and crash or timeout"),
        ("Issue Number", "348115"),
    ]

    for query_name, query in queries:
        console.print(f"[bold yellow]Scenario:[/bold yellow] {query_name}")
        console.print(f"[dim]User enters:[/dim] [cyan]\"{query}\"[/cyan]")
        console.print()

        # Step 1: Syntax Detection
        if is_ims_syntax(query):
            console.print("[green][OK][/green] IMS syntax detected, using as-is")
            final_query = query
            console.print(f"[dim]Final Query:[/dim] [green]{final_query}[/green]")
        else:
            console.print("[yellow][PARSING][/yellow]  Parsing natural language query...")

            # Step 2: Parse
            parser = NaturalLanguageParser()
            result = parser.parse(query)

            # Step 3: Show result table
            parse_table = Table(title="Query Parsing Result", show_header=False)
            parse_table.add_column("Field", style="cyan")
            parse_table.add_column("Value", style="green")

            parse_table.add_row("Original Query", query)
            parse_table.add_row("Parsed IMS Syntax", result.ims_query)
            parse_table.add_row("Language", result.language.upper())
            parse_table.add_row("Method", result.method.capitalize())
            parse_table.add_row("Confidence", f"{result.confidence:.1%}")
            parse_table.add_row("Explanation", result.explanation)

            console.print(parse_table)
            console.print()

            # Step 4: Confidence warning
            if result.confidence < 0.8:
                console.print(
                    f"[yellow][WARNING] Low confidence ({result.confidence:.1%}). "
                    "Please review parsed query carefully.[/yellow]"
                )
                console.print()

            # Step 5: Simulated confirmation
            console.print("[dim]User confirmation: [Y/n][/dim] [green]Y[/green]")
            final_query = result.ims_query
            console.print("[green][OK][/green] Using parsed query")

        console.print()
        console.print("[bold]─[/bold]" * 60)
        console.print()


def demo_comparison():
    """Show side-by-side comparison of old vs new workflow"""

    console.print(Panel.fit(
        "[bold cyan]Old vs New Workflow Comparison[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    comparison_table = Table(title="Feature Comparison")
    comparison_table.add_column("Feature", style="cyan")
    comparison_table.add_column("Old (IMS Syntax Only)", style="yellow")
    comparison_table.add_column("New (Natural Language)", style="green")

    comparison_table.add_row(
        "User Input",
        "Must learn IMS syntax\n'+error +crash'",
        "Natural language\n'find error and crash'"
    )
    comparison_table.add_row(
        "Learning Curve",
        "High - memorize operators",
        "Low - just describe what you want"
    )
    comparison_table.add_row(
        "Flexibility",
        "Manual syntax only",
        "Both natural language & IMS syntax"
    )
    comparison_table.add_row(
        "Confidence Check",
        "None",
        "Shows confidence score & preview"
    )
    comparison_table.add_row(
        "Batch Mode",
        "N/A",
        "Available with --no-confirm"
    )

    console.print(comparison_table)
    console.print()


def show_usage_examples():
    """Show practical usage examples"""

    console.print(Panel.fit(
        "[bold cyan]Practical Usage Examples[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    examples = [
        {
            "scenario": "Junior developer (doesn't know IMS syntax)",
            "old": "Must read documentation, learn +, ', operators",
            "new": 'Just type: "find error and crash"',
        },
        {
            "scenario": "Quick search during troubleshooting",
            "old": "python main.py crawl -p Tibero -k '+connection +timeout'",
            "new": 'python main.py crawl -p Tibero -k "find connection and timeout"',
        },
        {
            "scenario": "Automation script (batch processing)",
            "old": "Must pre-format queries as IMS syntax",
            "new": "Use natural language + --no-confirm flag",
        },
    ]

    for i, example in enumerate(examples, 1):
        console.print(f"[bold yellow]Example {i}:[/bold yellow] {example['scenario']}")
        console.print(f"  [dim]Old way:[/dim] {example['old']}")
        console.print(f"  [dim]New way:[/dim] [green]{example['new']}[/green]")
        console.print()


if __name__ == '__main__':
    demo_parsing_workflow()
    console.print()
    demo_comparison()
    console.print()
    show_usage_examples()

    console.print(Panel.fit(
        "[bold green][SUCCESS] Natural Language Parsing Successfully Integrated![/bold green]\n\n"
        "[cyan]Try it yourself:[/cyan]\n"
        "  python main.py crawl -p \"Tibero\" -k \"find error and crash\" -m 5\n\n"
        "[dim]Note: Requires IMS credentials configured in .env file[/dim]",
        border_style="green"
    ))
