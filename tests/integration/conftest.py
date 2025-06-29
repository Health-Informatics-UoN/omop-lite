import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from omop_lite.settings import Settings


@pytest.fixture(scope="session")
def test_database():
    """Create a test database for integration tests."""
    # Use environment variables or defaults for test database
    test_db_name = os.getenv("TEST_DB_NAME", "omop_test")
    db_host = os.getenv("TEST_DB_HOST", "localhost")
    db_port = int(os.getenv("TEST_DB_PORT", "5432"))
    db_user = os.getenv("TEST_DB_USER", "postgres")
    db_password = os.getenv("TEST_DB_PASSWORD", "password")

    # Connect to default database to create test database
    default_engine = create_engine(
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/postgres"
    )

    # Create test database if it doesn't exist
    with default_engine.connect() as conn:
        try:
            conn.execute(text(f"CREATE DATABASE {test_db_name}"))
            conn.commit()
        except ProgrammingError:
            # Database already exists, that's fine
            pass

    yield test_db_name

    # Cleanup: drop test database
    with default_engine.connect() as conn:
        try:
            # Terminate connections to the test database
            conn.execute(
                text(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()
            """)
            )
            conn.commit()

            # Drop the test database
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            conn.commit()
        except Exception:
            # Ignore cleanup errors
            pass

    default_engine.dispose()


@pytest.fixture
def integration_settings(test_database):
    """Create settings for integration tests."""
    return Settings(
        db_host=os.getenv("TEST_DB_HOST", "localhost"),
        db_port=int(os.getenv("TEST_DB_PORT", "5432")),
        db_user=os.getenv("TEST_DB_USER", "postgres"),
        db_password=os.getenv("TEST_DB_PASSWORD", "password"),
        db_name=test_database,
        schema_name="test_cdm",
        dialect="postgresql",
    )
