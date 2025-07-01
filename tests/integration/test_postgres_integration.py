import pytest
from sqlalchemy import inspect

from omop_lite.db.postgres import PostgresDatabase


@pytest.fixture
def test_db(integration_settings):
    """Create a test database connection."""
    # Create a test database instance
    db = PostgresDatabase(integration_settings)

    # Yield the database for tests
    yield db

    # Cleanup: drop all tables after each test
    try:
        db.drop_all(integration_settings.schema_name)
    except Exception:
        # Ignore cleanup errors
        pass


def test_create_schema_integration(test_db, integration_settings):
    """Integration test for schema creation."""
    # Test that schema doesn't exist initially
    assert not test_db.schema_exists(integration_settings.schema_name)

    # Create the schema
    test_db.create_schema(integration_settings.schema_name)

    # Verify the schema was created
    assert test_db.schema_exists(integration_settings.schema_name)

    # Verify we can see it in the database
    inspector = inspect(test_db.engine)
    schemas = inspector.get_schema_names()
    assert integration_settings.schema_name in schemas


def test_create_tables_integration(test_db, integration_settings):
    """Integration test for table creation."""
    # Create schema first
    test_db.create_schema(integration_settings.schema_name)

    # Create tables
    test_db.create_tables()

    # Verify tables were created
    inspector = inspect(test_db.engine)
    tables = inspector.get_table_names(schema=integration_settings.schema_name)

    # Check that key OMOP tables exist
    expected_tables = [
        "person",
        "concept",
        "condition_occurrence",
        "drug_exposure",
        "measurement",
        "observation",
        "visit_occurrence",
        "procedure_occurrence",
        "death",
        "observation_period",
        "cdm_source",
        "vocabulary",
        "domain",
    ]

    for table in expected_tables:
        assert table in tables, f"Table {table} was not created"

    # Check total number of tables (should be all OMOP tables)
    assert len(tables) == 39, f"Expected 39 tables, got {len(tables)}"

    # Verify table structure for a key table
    person_columns = inspector.get_columns(
        "person", schema=integration_settings.schema_name
    )
    person_column_names = [col["name"] for col in person_columns]

    expected_person_columns = [
        "person_id",
        "gender_concept_id",
        "year_of_birth",
        "month_of_birth",
        "day_of_birth",
        "birth_datetime",
        "race_concept_id",
        "ethnicity_concept_id",
        "location_id",
        "provider_id",
        "care_site_id",
        "person_source_value",
        "gender_source_value",
        "gender_source_concept_id",
        "race_source_value",
        "race_source_concept_id",
        "ethnicity_source_value",
        "ethnicity_source_concept_id",
    ]

    for col in expected_person_columns:
        assert col in person_column_names, f"Column {col} missing from person table"


def test_create_tables_twice_integration(test_db, integration_settings):
    """Test that creating tables twice doesn't fail."""
    # Create schema and tables first time
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Verify tables exist
    inspector = inspect(test_db.engine)
    tables_first = inspector.get_table_names(schema=integration_settings.schema_name)
    assert len(tables_first) == 39

    # Create tables second time (should not fail)
    test_db.create_tables()

    # Verify tables still exist
    tables_second = inspector.get_table_names(schema=integration_settings.schema_name)
    assert len(tables_second) == 39
    assert tables_first == tables_second


def test_drop_schema_integration(test_db, integration_settings):
    """Integration test for schema dropping."""
    # Create a schema first
    test_db.create_schema(integration_settings.schema_name)
    assert test_db.schema_exists(integration_settings.schema_name)

    # Drop the schema
    test_db.drop_schema(integration_settings.schema_name)

    # Verify the schema was dropped
    assert not test_db.schema_exists(integration_settings.schema_name)

    # Verify it's not in the database
    inspector = inspect(test_db.engine)
    schemas = inspector.get_schema_names()
    assert integration_settings.schema_name not in schemas


def test_schema_exists_integration(test_db, integration_settings):
    """Integration test for schema existence checking."""
    # Test non-existent schema
    assert not test_db.schema_exists("non_existent_schema")

    # Create a schema
    test_db.create_schema(integration_settings.schema_name)

    # Test existing schema
    assert test_db.schema_exists(integration_settings.schema_name)

    # Drop the schema
    test_db.drop_schema(integration_settings.schema_name)

    # Test dropped schema
    assert not test_db.schema_exists(integration_settings.schema_name)
