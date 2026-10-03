"""Drop tables and/or schema from the database."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from omop_lite.db import create_database
from ...utils import _create_settings

console = Console()


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
            help="Database dialect (postgresql, mssql or duckdb)",
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
