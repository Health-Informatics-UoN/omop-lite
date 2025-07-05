import pytest
import os

from omop_lite.settings import Settings
from omop_lite.db.postgres import PostgresDatabase
from omop_lite.db.sqlserver import SQLServerDatabase


@pytest.fixture
def integration_settings(request: pytest.FixtureRequest):
    """
    Create settings for integration tests based on the database class being tested.
    """
    # Get the database class from the parameterized test
    db_class = request.getfixturevalue("db_class")

    if db_class == PostgresDatabase:
        # Use PostgreSQL environment variables
        return Settings(
            db_host=os.getenv("POSTGRES_DB_HOST", "localhost"),
            db_port=int(os.getenv("POSTGRES_DB_PORT", "5432")),
            db_user=os.getenv("POSTGRES_DB_USERNAME", "postgres"),
            db_password=os.getenv("POSTGRES_DB_PASSWORD", "postgres"),
            db_name=os.getenv("POSTGRES_DB_DATABASE", "omop"),
            schema_name=os.getenv("POSTGRES_DB_SCHEMA", "test_cdm"),
            dialect="postgresql",
        )
    elif db_class == SQLServerDatabase:
        # Use SQL Server environment variables
        return Settings(
            db_host=os.getenv("SQLSERVER_DB_HOST", "localhost"),
            db_port=int(os.getenv("SQLSERVER_DB_PORT", "1433")),
            db_user=os.getenv("SQLSERVER_DB_USERNAME", "sa"),
            db_password=os.getenv("SQLSERVER_DB_PASSWORD", "Password123!"),
            db_name=os.getenv("SQLSERVER_DB_DATABASE", "master"),
            schema_name=os.getenv("SQLSERVER_DB_SCHEMA", "test_cdm"),
            dialect="mssql",
        )
    else:
        raise ValueError(f"Unsupported database class: {db_class}")
