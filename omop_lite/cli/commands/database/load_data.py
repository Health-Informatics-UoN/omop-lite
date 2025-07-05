"""Load data into existing tables."""

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


def load_data_command() -> typer.Typer:
    """Load data into existing tables."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def load_data(
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
        synthetic: bool = typer.Option(
            False, "--synthetic", envvar="SYNTHETIC", help="Use synthetic data"
        ),
        synthetic_number: int = typer.Option(
            100,
            "--synthetic-number",
            envvar="SYNTHETIC_NUMBER",
            help="Number of synthetic records",
        ),
        data_dir: str = typer.Option(
            "data", "--data-dir", envvar="DATA_DIR", help="Data directory"
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
        delimiter: str = typer.Option(
            "\t", "--delimiter", envvar="DELIMITER", help="CSV delimiter"
        ),
    ) -> None:
        """
        Load data into existing tables.

        This command loads data into tables that must already exist.
        Use create-tables first if tables don't exist.
        """
        settings = _create_settings(
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
            synthetic=synthetic,
            synthetic_number=synthetic_number,
            data_dir=data_dir,
            schema_name=schema_name,
            dialect=dialect,
            log_level=log_level,
            delimiter=delimiter,
        )

        db = create_database(settings)

        # Load data with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[yellow]Loading data...", total=1)
            db.load_data()
            progress.update(task, completed=1)

        console.print(
            Panel(
                "[bold green]✅ Data loaded successfully![/bold green]",
                title="📊 Data Loading Complete",
                border_style="green",
            )
        )

    return app
