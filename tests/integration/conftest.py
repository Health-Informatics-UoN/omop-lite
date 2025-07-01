import pytest
import os

from omop_lite.settings import Settings


@pytest.fixture
def integration_settings():
    """Create settings for integration tests."""
    return Settings(
        db_host=os.getenv("TEST_DB_HOST", "localhost"),
        db_port=int(os.getenv("TEST_DB_PORT", "5432")),
        db_user=os.getenv("TEST_DB_USER", "postgres"),
        db_password=os.getenv("TEST_DB_PASSWORD", "password"),
        db_name=os.getenv("TEST_DB_NAME", "omop_test"),
        schema_name="test_cdm",
        dialect="postgresql",
    )
