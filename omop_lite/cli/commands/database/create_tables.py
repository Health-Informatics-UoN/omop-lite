"""Create only the database tables."""

import typer

from omop_lite.db import create_database
from ...utils import _create_settings, _setup_logging


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
