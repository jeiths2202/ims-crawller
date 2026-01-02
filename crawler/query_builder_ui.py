"""
Interactive Query Builder UI

Terminal-based interactive query builder for IMS Crawler.
Provides guided query construction with real-time preview.
"""
import sys
from typing import List, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns

from crawler.history_manager import HistoryManager, QueryRecord


console = Console()


class InteractiveQueryBuilder:
    """
    Interactive terminal UI for building IMS queries

    Features:
    - Step-by-step query construction
    - Load from favorites or history
    - Real-time preview
    - Multi-language support
    """

    PRODUCTS = [
        "Tibero",
        "JEUS",
        "OpenFrame",
        "WebtoB",
        "ProFrame",
        "OFCOBOL",
        "OFPLI",
        "Other"
    ]

    QUERY_TYPES = [
        ("and", "AND Query (All terms required)", "+term1 +term2"),
        ("or", "OR Query (Any term matches)", "term1 term2"),
        ("phrase", "Exact Phrase", "'exact phrase'"),
        ("mixed", "Mixed Query (Advanced)", "term1 +term2 'phrase'"),
        ("direct", "Direct IMS Syntax (Advanced)", "Enter raw IMS syntax")
    ]

    def __init__(self):
        self.history_manager = HistoryManager()
        self.product = None
        self.query_type = None
        self.terms = []
        self.final_query = ""

    def run(self) -> dict:
        """
        Run interactive query builder

        Returns:
            dict: {
                'product': str,
                'query': str,
                'parsed_query': str,
                'max_results': int,
                'from_favorite': bool
            }
        """
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]🔨 Interactive Query Builder[/bold cyan]\n"
            "Build IMS search queries step-by-step",
            border_style="cyan"
        ))

        # Step 0: Load from favorites/history or build new?
        load_option = self._ask_load_option()

        if load_option == "favorite":
            return self._load_from_favorites()
        elif load_option == "history":
            return self._load_from_history()

        # Step 1: Select product
        self.product = self._ask_product()

        # Step 2: Select query type
        self.query_type = self._ask_query_type()

        # Step 3: Build query based on type
        if self.query_type == "direct":
            self.final_query = self._ask_direct_query()
        else:
            self.terms = self._ask_terms()
            self.final_query = self._build_query()

        # Step 4: Preview and confirm
        confirmed = self._preview_and_confirm()

        if not confirmed:
            console.print("[yellow]Query building cancelled[/yellow]")
            sys.exit(0)

        # Step 5: Additional options
        max_results = self._ask_max_results()

        return {
            'product': self.product,
            'query': self.final_query,
            'parsed_query': self.final_query,  # Already in IMS syntax
            'max_results': max_results,
            'from_favorite': False
        }

    def _ask_load_option(self) -> str:
        """Ask if user wants to load from favorites/history"""
        console.print("\n[bold]Start from:[/bold]")
        console.print("  [cyan]1.[/cyan] Build new query")
        console.print("  [cyan]2.[/cyan] Load from favorites")
        console.print("  [cyan]3.[/cyan] Load from history")

        choice = Prompt.ask(
            "\n[yellow]Your choice[/yellow]",
            choices=["1", "2", "3"],
            default="1"
        )

        if choice == "2":
            return "favorite"
        elif choice == "3":
            return "history"
        return "new"

    def _load_from_favorites(self) -> Optional[dict]:
        """Load query from favorites"""
        favs = self.history_manager.get_favorites()

        if not favs:
            console.print("[yellow]No favorites found. Building new query...[/yellow]")
            return self.run()  # Start from beginning

        # Display favorites
        table = Table(title="⭐ Your Favorite Queries")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Product", style="green", width=12)
        table.add_column("Query", style="white", width=50)

        for idx, fav in enumerate(favs):
            table.add_row(
                str(idx),
                fav.product,
                fav.query[:50]
            )

        console.print(table)

        # Select favorite
        choice = Prompt.ask(
            "\n[yellow]Select favorite (or 'c' to cancel)[/yellow]",
            default="0"
        )

        if choice.lower() == 'c':
            return self.run()  # Start from beginning

        try:
            idx = int(choice)
            if 0 <= idx < len(favs):
                fav = favs[idx]
                return {
                    'product': fav.product,
                    'query': fav.query,
                    'parsed_query': fav.parsed_query,
                    'max_results': 50,
                    'from_favorite': True
                }
        except ValueError:
            pass

        console.print("[red]Invalid selection[/red]")
        return self._load_from_favorites()

    def _load_from_history(self) -> Optional[dict]:
        """Load query from history"""
        history = self.history_manager.get_history(limit=10)

        if not history:
            console.print("[yellow]No history found. Building new query...[/yellow]")
            return self.run()  # Start from beginning

        # Display history
        table = Table(title="📜 Recent Queries")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Product", style="green", width=12)
        table.add_column("Query", style="white", width=50)
        table.add_column("Results", style="yellow", width=8)

        for idx, record in enumerate(history):
            table.add_row(
                str(idx),
                record.product,
                record.query[:50],
                str(record.results_count)
            )

        console.print(table)

        # Select history item
        choice = Prompt.ask(
            "\n[yellow]Select query (or 'c' to cancel)[/yellow]",
            default="0"
        )

        if choice.lower() == 'c':
            return self.run()  # Start from beginning

        try:
            idx = int(choice)
            if 0 <= idx < len(history):
                record = history[idx]
                return {
                    'product': record.product,
                    'query': record.query,
                    'parsed_query': record.parsed_query,
                    'max_results': 50,
                    'from_favorite': False
                }
        except ValueError:
            pass

        console.print("[red]Invalid selection[/red]")
        return self._load_from_history()

    def _ask_product(self) -> str:
        """Ask user to select product"""
        console.print("\n[bold]Step 1: Select Product[/bold]")

        for idx, product in enumerate(self.PRODUCTS, 1):
            console.print(f"  [cyan]{idx}.[/cyan] {product}")

        choice = Prompt.ask(
            "\n[yellow]Select product (1-8 or type custom)[/yellow]",
            default="1"
        )

        try:
            idx = int(choice)
            if 1 <= idx <= len(self.PRODUCTS):
                if idx == len(self.PRODUCTS):  # "Other"
                    return Prompt.ask("[yellow]Enter product name[/yellow]")
                return self.PRODUCTS[idx - 1]
        except ValueError:
            # User typed custom product name
            return choice

        console.print("[red]Invalid selection[/red]")
        return self._ask_product()

    def _ask_query_type(self) -> str:
        """Ask user to select query type"""
        console.print("\n[bold]Step 2: Select Query Type[/bold]")

        for idx, (key, desc, example) in enumerate(self.QUERY_TYPES, 1):
            console.print(f"  [cyan]{idx}.[/cyan] {desc}")
            console.print(f"      [dim]Example: {example}[/dim]")

        choice = Prompt.ask(
            "\n[yellow]Select query type (1-5)[/yellow]",
            choices=["1", "2", "3", "4", "5"],
            default="1"
        )

        idx = int(choice) - 1
        return self.QUERY_TYPES[idx][0]

    def _ask_direct_query(self) -> str:
        """Ask user to enter direct IMS syntax"""
        console.print("\n[bold]Direct IMS Syntax[/bold]")
        console.print("[dim]Enter your query using IMS syntax directly[/dim]")
        console.print("[dim]Syntax: +required term 'exact phrase' optional[/dim]")

        query = Prompt.ask("\n[yellow]IMS Query[/yellow]")
        return query

    def _ask_terms(self) -> List[str]:
        """Ask user to enter search terms"""
        console.print("\n[bold]Step 3: Enter Search Terms[/bold]")

        if self.query_type == "phrase":
            console.print("[dim]Enter the exact phrase to search for[/dim]")
            phrase = Prompt.ask("[yellow]Exact phrase[/yellow]")
            return [phrase]

        console.print("[dim]Enter terms one by one (empty to finish)[/dim]")
        console.print(f"[dim]Query type: {self.query_type.upper()}[/dim]")

        terms = []
        while True:
            term = Prompt.ask(
                f"[yellow]Term #{len(terms) + 1}[/yellow] (or Enter to finish)",
                default=""
            )

            if not term:
                break

            terms.append(term)

            # Show current preview
            preview = self._build_query_preview(terms)
            console.print(f"[dim]Preview: {preview}[/dim]")

        if not terms:
            console.print("[yellow]No terms entered. Please enter at least one term.[/yellow]")
            return self._ask_terms()

        return terms

    def _build_query_preview(self, terms: List[str]) -> str:
        """Build query preview from current terms"""
        if not terms:
            return ""

        if self.query_type == "and":
            return " ".join([f"+{term}" for term in terms])
        elif self.query_type == "or":
            return " ".join(terms)
        elif self.query_type == "phrase":
            return f"'{terms[0]}'"
        elif self.query_type == "mixed":
            return " ".join(terms)  # User can use +/quotes themselves
        else:
            return " ".join(terms)

    def _build_query(self) -> str:
        """Build final IMS query from terms"""
        return self._build_query_preview(self.terms)

    def _preview_and_confirm(self) -> bool:
        """Show preview and ask for confirmation"""
        console.print("\n" + "="*60)
        console.print(Panel.fit(
            f"[bold]Product:[/bold] [green]{self.product}[/green]\n"
            f"[bold]Query Type:[/bold] [yellow]{self.query_type.upper()}[/yellow]\n"
            f"[bold]IMS Query:[/bold] [cyan]{self.final_query}[/cyan]",
            title="🔍 Query Preview",
            border_style="cyan"
        ))

        return Confirm.ask("\n[yellow]Execute this query?[/yellow]", default=True)

    def _ask_max_results(self) -> int:
        """Ask user for max results"""
        default_max = "50"
        max_str = Prompt.ask(
            "\n[yellow]Maximum results[/yellow]",
            default=default_max
        )

        try:
            return int(max_str)
        except ValueError:
            console.print(f"[red]Invalid number, using default: {default_max}[/red]")
            return int(default_max)
