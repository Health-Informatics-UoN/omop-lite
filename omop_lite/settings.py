from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Settings for OMOP Lite."""

    db_host: str = "db"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "password"
    db_name: str = "omop"
    synthetic: bool = False
    synthetic_number: int = 100
    data_dir: str = "data"
    schema_name: str = "public"
    dialect: Literal["postgresql", "mssql"] = "postgresql"
    log_level: str = "INFO"
    fts_create: bool = False
    delimiter: str = "\t"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
