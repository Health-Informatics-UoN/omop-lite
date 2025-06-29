import pytest
from sqlalchemy import inspect

from omop_lite.settings import Settings
from omop_lite.db.postgres import PostgresDatabase


@pytest.fixture
def test_settings():
    """Create test settings for integration testing."""
    return Settings(
        db_host="localhost",
        db_port=5432,
        db_user="postgres",
        db_password="password",
        db_name="omop_test",  # Use a test database
        schema_name="test_cdm",
        dialect="postgresql",
    )


@pytest.fixture
def test_db(test_settings):
    """Create a test database connection."""
    # Create a test database instance
    db = PostgresDatabase(test_settings)

    # Yield the database for tests
    yield db

    # Cleanup: drop the schema after each test
    try:
        db.drop_schema(test_settings.schema_name)
    except Exception:
        # Ignore cleanup errors
        pass


def test_create_schema_integration(test_db, test_settings):
    """Integration test for schema creation."""
    # Test that schema doesn't exist initially
    assert not test_db.schema_exists(test_settings.schema_name)

    # Create the schema
    test_db.create_schema(test_settings.schema_name)

    # Verify the schema was created
    assert test_db.schema_exists(test_settings.schema_name)

    # Verify we can see it in the database
    inspector = inspect(test_db.engine)
    schemas = inspector.get_schema_names()
    assert test_settings.schema_name in schemas


def test_create_schema_twice_integration(test_db, test_settings):
    """Test that creating the same schema twice doesn't fail."""
    # Create schema first time
    test_db.create_schema(test_settings.schema_name)
    assert test_db.schema_exists(test_settings.schema_name)

    # Create schema second time (should not fail)
    test_db.create_schema(test_settings.schema_name)
    assert test_db.schema_exists(test_settings.schema_name)


def test_drop_schema_integration(test_db, test_settings):
    """Integration test for schema dropping."""
    # Create a schema first
    test_db.create_schema(test_settings.schema_name)
    assert test_db.schema_exists(test_settings.schema_name)

    # Drop the schema
    test_db.drop_schema(test_settings.schema_name)

    # Verify the schema was dropped
    assert not test_db.schema_exists(test_settings.schema_name)

    # Verify it's not in the database
    inspector = inspect(test_db.engine)
    schemas = inspector.get_schema_names()
    assert test_settings.schema_name not in schemas


def test_schema_exists_integration(test_db, test_settings):
    """Integration test for schema existence checking."""
    # Test non-existent schema
    assert not test_db.schema_exists("non_existent_schema")

    # Create a schema
    test_db.create_schema(test_settings.schema_name)

    # Test existing schema
    assert test_db.schema_exists(test_settings.schema_name)

    # Drop the schema
    test_db.drop_schema(test_settings.schema_name)

    # Test dropped schema
    assert not test_db.schema_exists(test_settings.schema_name)
