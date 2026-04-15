from typing import Literal
from omop_lite.settings import Settings
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
    dialect: Literal["postgresql", "mssql"] = "postgresql",
    omop_version: Literal["omop5_3", "omop5_4"] = "omop5_4",
    log_level: str = "INFO",
    fts_create: bool = False,
    delimiter: str = "\t",
) -> Settings:
    """Create settings with validation."""
    # Validate dialect
    # I think this should just let pydantic handle it - as these are both Literals in the model, it will throw a validation error anyway
    # Keeping existing logic for now
    if dialect not in ["postgresql", "mssql"]:
        raise typer.BadParameter("dialect must be either 'postgresql' or 'mssql'")
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
