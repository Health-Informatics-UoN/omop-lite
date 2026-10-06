"""Add only primary keys to existing tables."""

from typing import Literal

import typer

from omop_lite.db import create_database

from ...utils import _create_settings, _format_batch_summary, _setup_logging


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
            help="Database dialect (postgresql, mssql or duckdb)",
        ),
        omop_version: Literal["omop5_3", "omop5_4", "omop5_5"] = typer.Option(
            "omop5_4",
            "--omop_version",
            envvar="OMOP_VERSION",
            help="Version of the OMOP CDM (omop5_5, omop5_4 or omop5_3)",
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
            omop_version=omop_version,
            log_level=log_level,
        )

        logger = _setup_logging(settings)
        db = create_database(settings)

        # Add primary keys only. A failed statement is never fatal here -
        # real OMOP data can have rows that don't satisfy every key.
        result = db.add_primary_keys()
        logger.info(_format_batch_summary(result, "Primary keys"))

    return app
