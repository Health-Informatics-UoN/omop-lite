from pydantic_settings import BaseSettings
from typing import Literal
from pydantic import Field


class Settings(BaseSettings):
    """Settings for OMOP Lite."""

    db_host: str = Field(default="db", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_user: str = Field(default="postgres", description="Database user")
    db_password: str = Field(default="password", description="Database password")
    db_name: str = Field(default="omop", description="Database name")
    synthetic: bool = Field(default=False, description="Use synthetic data")
    synthetic_number: int = Field(
        default=100, description="Number of synthetic records"
    )
    data_dir: str = Field(default="data", description="Data directory")
    schema_name: str = Field(default="public", description="Database schema name")
    dialect: Literal["postgresql", "mssql"] = Field(
        default="postgresql", description="Database dialect"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    fts_create: bool = Field(
        default=False, description="Create full-text search indexes"
    )
    delimiter: str = Field(default="\t", description="CSV delimiter")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
