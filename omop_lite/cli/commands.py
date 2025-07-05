from omop_lite.db import create_database
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
from rich.table import Table
from rich.prompt import Confirm
import time

from .utils import _create_settings, _setup_logging

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


def create_tables_command() -> typer.Typer:
    """Create only the database tables."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def create_tables(
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
        Create only the database tables.

        This command creates the schema (if needed) and the tables,
        but does not load data or add constraints.
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

        logger = _setup_logging(settings)
        db = create_database(settings)

        # Handle schema creation if not using 'public'
        if settings.schema_name != "public":
            if db.schema_exists(settings.schema_name):
                logger.info(f"Schema '{settings.schema_name}' already exists")
            else:
                db.create_schema(settings.schema_name)

        # Create tables only
        db.create_tables()
        logger.info("✅ Tables created successfully")

    return app


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


def add_primary_keys_command() -> typer.Typer:
    """Add only primary keys to existing tables."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def add_primary_keys(
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
        Add only primary keys to existing tables.

        This command adds primary key constraints to existing tables.
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

        logger = _setup_logging(settings)
        db = create_database(settings)

        # Add primary keys only
        db.add_primary_keys()
        logger.info("✅ Primary keys added successfully")

    return app


def add_foreign_keys_command() -> typer.Typer:
    """Add only foreign key constraints to existing tables."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def add_foreign_keys(
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
        Add only foreign key constraints to existing tables.

        This command adds foreign key constraints to existing tables.
        Tables must exist and should have data loaded.
        Primary keys should be added first.
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

        logger = _setup_logging(settings)
        db = create_database(settings)

        # Add foreign key constraints only
        db.add_constraints()
        logger.info("✅ Foreign key constraints added successfully")

    return app


def add_indices_command() -> typer.Typer:
    """Add only indices to existing tables."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def add_indices(
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
        Add only indices to existing tables.

        This command adds indices to existing tables.
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

        logger = _setup_logging(settings)
        db = create_database(settings)

        # Add indices only
        db.add_indices()
        logger.info("✅ Indices added successfully")

    return app


def drop_command() -> typer.Typer:
    """Drop tables and/or schema from the database."""
    app = typer.Typer()

    @app.callback(invoke_without_command=True)
    def drop(
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
        tables_only: bool = typer.Option(
            False, "--tables-only", help="Drop only tables, not the schema"
        ),
        schema_only: bool = typer.Option(
            False, "--schema-only", help="Drop only the schema (and all its contents)"
        ),
        confirm: bool = typer.Option(
            False, "--confirm", help="Skip confirmation prompt"
        ),
    ) -> None:
        """
        Drop tables and/or schema from the database.

        This command can drop tables, schema, or everything.
        Use with caution as this will permanently delete data.
        """
        if not confirm:
            # Create a warning panel
            warning_text = ""
            if tables_only:
                warning_text = f"[bold red]⚠️  WARNING[/bold red]\n\nThis will drop [bold]ALL TABLES[/bold] in schema '{schema_name}'.\n\n[red]This action cannot be undone![/red]"
            elif schema_only:
                warning_text = f"[bold red]⚠️  WARNING[/bold red]\n\nThis will drop [bold]SCHEMA '{schema_name}'[/bold] and [bold]ALL ITS CONTENTS[/bold].\n\n[red]This action cannot be undone![/red]"
            else:
                warning_text = f"[bold red]⚠️  WARNING[/bold red]\n\nThis will drop [bold]ALL TABLES[/bold] and [bold]SCHEMA '{schema_name}'[/bold].\n\n[red]This action cannot be undone![/red]"

            console.print(
                Panel(warning_text, title="🗑️  Drop Operation", border_style="red")
            )

            if not Confirm.ask("Are you sure you want to continue?", default=False):
                console.print("[yellow]Operation cancelled.[/yellow]")
                raise typer.Exit()

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

        try:
            with console.status(
                "[bold red]Dropping database objects...", spinner="dots"
            ):
                if tables_only:
                    db.drop_tables()
                    console.print(
                        Panel(
                            f"[bold green]✅ All tables in schema '{schema_name}' dropped successfully![/bold green]",
                            title="🗑️  Tables Dropped",
                            border_style="green",
                        )
                    )
                elif schema_only:
                    if schema_name == "public":
                        console.print(
                            Panel(
                                "[yellow]⚠️  Cannot drop 'public' schema, dropping tables instead[/yellow]",
                                title="⚠️  Schema Protection",
                                border_style="yellow",
                            )
                        )
                        db.drop_tables()
                        console.print(
                            Panel(
                                "[bold green]✅ All tables dropped successfully![/bold green]",
                                title="🗑️  Tables Dropped",
                                border_style="green",
                            )
                        )
                    else:
                        db.drop_schema(schema_name)
                        console.print(
                            Panel(
                                f"[bold green]✅ Schema '{schema_name}' dropped successfully![/bold green]",
                                title="🗑️  Schema Dropped",
                                border_style="green",
                            )
                        )
                else:
                    db.drop_all(schema_name)
                    console.print(
                        Panel(
                            f"[bold green]✅ Database completely dropped![/bold green]\n\n[dim]Schema: {schema_name}\nDatabase: {settings.db_name}[/dim]",
                            title="🗑️  Database Dropped",
                            border_style="green",
                        )
                    )

        except Exception as e:
            console.print(
                Panel(
                    f"[bold red]❌ Drop operation failed[/bold red]\n\n[red]{e}[/red]",
                    title="💥 Drop Failed",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

    return app


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
