from typing import Literal
from omop_lite.settings import Settings
from omop_lite.db.base import SqlBatchResult
import logging
import typer
from importlib.metadata import version


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
    dialect: Literal["postgresql", "mssql", "duckdb"] = "postgresql",
    omop_version: Literal["omop5_3", "omop5_4"] = "omop5_4",
    log_level: str = "INFO",
    fts_create: bool = False,
    delimiter: str = "\t",
) -> Settings:
    """Create settings with validation."""
    # Validate dialect
    # I think this should just let pydantic handle it - as these are both Literals in the model, it will throw a validation error anyway
    # Keeping existing logic for now
    if dialect not in ["postgresql", "mssql", "duckdb"]:
        raise typer.BadParameter(
            "dialect must be one of 'postgresql', 'mssql' or 'duckdb'"
        )
    # Validate omop_version
    if omop_version not in ["omop5_3", "omop5_4"]:
        raise typer.BadParameter("omop version must be either 'omop5_3' or 'omop5_4'")

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
        omop_version=omop_version,
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


def _format_batch_summary(result: SqlBatchResult, label: str) -> str:
    """Summarise a SqlBatchResult for CLI output.

    A failed statement is never fatal (real OMOP vocabulary data routinely
    doesn't satisfy every constraint), so this is purely informational -
    callers should not treat a non-zero `failed` count as a reason to exit
    non-zero.
    """
    if result.failed:
        return (
            f"⚠️  {label}: {result.succeeded} of {result.total} applied, "
            f"{result.failed} failed - see the log above for details."
        )
    return f"✅ {label}: all {result.succeeded} applied."
