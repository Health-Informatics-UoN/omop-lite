"""Add all constraints (primary keys, foreign keys, and indices)."""

import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.panel import Panel

from omop_lite.db import create_database
from ...utils import _create_settings

console = Console()


def add_constraints_command() -> typer.Typer:
    """Add all constraints (primary keys, foreign keys, and indices)."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def add_constraints(
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
        Add all constraints (primary keys, foreign keys, and indices).

        This command adds all types of constraints to existing tables.
        Tables must exist and should have data loaded.
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

        db = create_database(settings)

        # Add all constraints with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[green]Adding constraints...", total=3)

            # Primary keys
            progress.update(task, description="[cyan]Adding primary keys...")
            db.add_primary_keys()
            progress.advance(task)

            # Foreign keys
            progress.update(task, description="[cyan]Adding foreign key constraints...")
            db.add_constraints()
            progress.advance(task)

            # Indices
            progress.update(task, description="[cyan]Adding indices...")
            db.add_indices()
            progress.advance(task)

        console.print(
            Panel(
                "[bold green]✅ All constraints added successfully![/bold green]\n\n"
                "[dim]• Primary keys\n"
                "• Foreign key constraints\n"
                "• Indices[/dim]",
                title="🔗 Constraints Added",
                border_style="green",
            )
        )

    return app
