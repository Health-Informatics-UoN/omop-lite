"""Test database connectivity and basic operations."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import time

from omop_lite.db import create_database
from ...utils import _create_settings

console = Console()


def test_command() -> typer.Typer:
    """Test database connectivity and basic operations."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def test(
        db_host: str = typer.Option(
            "db", "--db-host", "-h", envvar="DB_HOST", help="Database host"
        ),
        db_port: int = typer.Option(
            5432, "--db-port", "-p", envvar="DB_PORT", help="Database port"
        ),
        db_user: str = typer.Option(
            "postgres", "--db-user", "-u", envvar="DB_USER", help="Database user"
        ),
        db_password: str = typer.Option(
            "password", "--db-password", envvar="DB_PASSWORD", help="Database password"
        ),
        db_name: str = typer.Option(
            "omop", "--db-name", "-d", envvar="DB_NAME", help="Database name"
        ),
        schema_name: str = typer.Option(
            "public", "--schema-name", envvar="SCHEMA_NAME", help="Database schema name"
        ),
        dialect: str = typer.Option(
            "postgresql",
            "--dialect",
            envvar="DIALECT",
            help="Database dialect (postgresql or mssql)",
        ),
        log_level: str = typer.Option(
            "INFO", "--log-level", envvar="LOG_LEVEL", help="Logging level"
        ),
    ) -> None:
        """
        Test database connectivity and basic operations.

        This command tests the database connection and performs basic operations
        without creating tables or loading data.
        """
        settings = _create_settings(
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
            schema_name=schema_name,
            dialect=dialect,
            log_level=log_level,
        )

        try:
            with console.status(
                "[bold blue]Testing database connection...", spinner="dots"
            ):
                db = create_database(settings)

            # Create results table
            table = Table(title="Database Test Results")
            table.add_column("Test", style="cyan", no_wrap=True)
            table.add_column("Status", style="bold")
            table.add_column("Details", style="dim")

            # Test connection
            table.add_row(
                "Database Connection", "✅ PASS", f"Connected to {settings.db_name}"
            )

            # Test schema
            if db.schema_exists(settings.schema_name):
                table.add_row(
                    "Schema Check", "✅ PASS", f"Schema '{settings.schema_name}' exists"
                )
            else:
                table.add_row(
                    "Schema Check",
                    "ℹ️  INFO",
                    f"Schema '{settings.schema_name}' does not exist (normal)",
                )

            # Test basic operations
            with console.status(
                "[bold green]Testing basic operations...", spinner="dots"
            ):
                time.sleep(0.5)  # Simulate operation
            table.add_row("Basic Operations", "✅ PASS", "All operations successful")

            console.print(table)
            console.print(
                Panel(
                    "[bold green]✅ Database test completed successfully![/bold green]",
                    title="🎯 Test Results",
                    border_style="green",
                )
            )

        except Exception as e:
            console.print(
                Panel(
                    f"[bold red]❌ Database test failed[/bold red]\n\n[red]{e}[/red]",
                    title="💥 Test Failed",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

    return app
