from omop_lite.settings import Settings
from omop_lite.db import create_database
import logging
from importlib.metadata import version
import typer


app = typer.Typer(
    name="omop-lite",
    help="Get an OMOP CDM database running quickly.",
    add_completion=False,
    no_args_is_help=False,
)


def _create_settings(
    db_host: str = "db",
    db_port: int = 5432,
    db_user: str = "postgres",
    db_password: str = "password",
    db_name: str = "omop",
    synthetic: bool = False,
    synthetic_number: int = 100,
    data_dir: str = "data",
    schema_name: str = "public",
    dialect: str = "postgresql",
    log_level: str = "INFO",
    fts_create: bool = False,
    delimiter: str = "\t",
) -> Settings:
    """Create settings with validation."""
    # Validate dialect
    if dialect not in ["postgresql", "mssql"]:
        raise typer.BadParameter("dialect must be either 'postgresql' or 'mssql'")

    return Settings(
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


def _setup_logging(settings: Settings) -> logging.Logger:
    """Setup logging with the given settings."""
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting OMOP Lite {version('omop-lite')}")
    logger.debug(f"Settings: {settings.model_dump()}")
    return logger


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

        logger = _setup_logging(settings)
        db = create_database(settings)

        # Handle schema creation if not using 'public'
        if settings.schema_name != "public":
            if db.schema_exists(settings.schema_name):
                logger.info(f"Schema '{settings.schema_name}' already exists")
                return
            else:
                db.create_schema(settings.schema_name)

        # Continue with table creation, data loading, etc.
        db.create_tables()
        db.load_data()
        db.add_constraints()

        logger.info("OMOP Lite database created successfully")


@app.command()
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
        dialect=dialect,
        log_level=log_level,
    )

    logger = _setup_logging(settings)

    try:
        db = create_database(settings)
        logger.info("✅ Database connection successful")

        # Test basic operations
        if db.schema_exists("public"):
            logger.info("✅ Public schema exists")
        else:
            logger.info("ℹ️  Public schema does not exist (this is normal)")

        logger.info("✅ Database test completed successfully")

    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        raise typer.Exit(1)


def main_cli():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main_cli()
