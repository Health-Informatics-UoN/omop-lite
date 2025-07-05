"""Help-related CLI commands."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def help_commands_command() -> typer.Typer:
    """Show detailed help for all available commands."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def help_commands() -> None:
        """
        Show detailed help for all available commands.
        """
        table = Table(
            title="OMOP Lite Commands", show_header=True, header_style="bold magenta"
        )
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Use Case", style="dim")

        table.add_row(
            "[default]",
            "Create complete OMOP database (tables + data + constraints)",
            "Quick start, development, Docker",
        )
        table.add_row(
            "test",
            "Test database connectivity and basic operations",
            "Verify connection, troubleshoot",
        )
        table.add_row(
            "create-tables",
            "Create only the database tables",
            "Step-by-step setup, custom workflows",
        )
        table.add_row(
            "load-data",
            "Load data into existing tables",
            "Reload data, update datasets",
        )
        table.add_row(
            "add-constraints",
            "Add all constraints (primary keys, foreign keys, indices)",
            "Complete constraint setup",
        )
        table.add_row(
            "add-primary-keys",
            "Add only primary key constraints",
            "Granular constraint control",
        )
        table.add_row(
            "add-foreign-keys",
            "Add only foreign key constraints",
            "Granular constraint control",
        )
        table.add_row("add-indices", "Add only indices", "Granular constraint control")
        table.add_row("drop", "Drop tables and/or schema", "Cleanup, reset database")
        table.add_row(
            "help-commands", "Show this help table", "Discover available commands"
        )

        console.print(table)
        console.print(
            Panel(
                "[bold blue]💡 Tip:[/bold blue] Use [cyan]omop-lite <command> --help[/cyan] for detailed command options\n\n"
                "[bold green]🚀 Quick Start:[/bold green] [cyan]omop-lite --synthetic[/cyan]",
                title="ℹ️  Usage Tips",
                border_style="blue",
            )
        )

    return app
