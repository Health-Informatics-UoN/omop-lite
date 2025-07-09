from omop_lite.db import create_database
from importlib.metadata import version
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

from .utils import _create_settings

console = Console()

app = typer.Typer(
    name="omop-lite",
    help="Get an OMOP CDM database running quickly.",
    add_completion=False,
    no_args_is_help=False,
)

# Import and add all subcommands
from .commands import (  # noqa: E402
    test_command,
    create_tables_command,
    load_data_command,
    add_constraints_command,
    add_primary_keys_command,
    add_foreign_keys_command,
    add_indices_command,
    drop_command,
    help_commands_command,
)

app.add_typer(test_command(), name="test")
app.add_typer(create_tables_command(), name="create-tables")
app.add_typer(load_data_command(), name="load-data")
app.add_typer(add_constraints_command(), name="add-constraints")
app.add_typer(add_primary_keys_command(), name="add-primary-keys")
app.add_typer(add_foreign_keys_command(), name="add-foreign-keys")
app.add_typer(add_indices_command(), name="add-indices")
app.add_typer(drop_command(), name="drop")
app.add_typer(help_commands_command(), name="help-commands")


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
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
    fts_create: bool = typer.Option(
        False,
        "--fts-create",
        envvar="FTS_CREATE",
        help="Create full-text search indexes",
    ),
    delimiter: str = typer.Option(
        "\t", "--delimiter", envvar="DELIMITER", help="CSV delimiter"
    ),
    required_tables: list[str] = typer.Option(
        [],
        "--required-tables",
        envvar="REQUIRED_TABLES",
        help="Required tables to load",
    ),
) -> None:
    """
    Create the OMOP Lite database (default command).

    This command will create the schema if it doesn't exist,
    create the tables, load the data, and run the update migrations.

    All settings can be configured via environment variables or command-line arguments.
    Command-line arguments take precedence over environment variables.
    """
    if ctx.invoked_subcommand is None:
        # This is the default command (no subcommand specified)
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
            fts_create=fts_create,
            delimiter=delimiter,
        )

        # Show startup info
        console.print(
            Panel(
                f"[bold blue]OMOP Lite[/bold blue] v{version('omop-lite')}\n"
                f"[dim]Creating OMOP CDM database...[/dim]",
                title="🚀 Starting Pipeline",
                border_style="blue",
            )
        )

        db = create_database(settings)

        # Handle schema creation if not using 'public'
        if settings.schema_name != "public":
            if db.schema_exists(settings.schema_name):
                console.print(f"ℹ️  Schema '{settings.schema_name}' already exists")
                return
            else:
                with console.status("[bold green]Creating schema...", spinner="dots"):
                    db.create_schema(settings.schema_name)
                console.print(f"✅ Schema '{settings.schema_name}' created")

        # Progress bar for the main pipeline
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            # Create tables
            task1 = progress.add_task("[cyan]Creating tables...", total=1)
            db.create_tables()
            progress.update(task1, completed=1)

            # Load data
            task2 = progress.add_task("[yellow]Loading data...", total=1)
            db.load_data(required_tables)
            progress.update(task2, completed=1)

            # Add constraints
            task3 = progress.add_task("[green]Adding constraints...", total=1)
            db.add_all_constraints()
            progress.update(task3, completed=1)

        console.print(
            Panel(
                "[bold green]✅ OMOP Lite database created successfully![/bold green]\n"
                f"[dim]Database: {settings.db_name}\n"
                f"Schema: {settings.schema_name}\n"
                f"Dialect: {settings.dialect}[/dim]",
                title="🎉 Success",
                border_style="green",
            )
        )


def main_cli():
    """Entry point for the CLI."""
    app()
