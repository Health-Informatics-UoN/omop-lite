from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Settings for OMOP Lite."""

    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    synthetic: bool
    data_dir: str
    schema_name: str
    db_type: Literal["postgresql", "sqlite"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
