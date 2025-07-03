import pytest
from sqlalchemy import inspect, text

from omop_lite.db.postgres import PostgresDatabase
from omop_lite.settings import Settings


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


def test_create_schema_integration(
    test_db: PostgresDatabase, integration_settings: Settings
):
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


def test_create_tables_integration(
    test_db: PostgresDatabase, integration_settings: Settings
):
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


def test_add_primary_keys_integration(
    test_db: PostgresDatabase, integration_settings: Settings
):
    """Integration test for adding primary keys."""
    # Create schema and tables
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Add primary keys
    test_db.add_primary_keys()

    # Verify primary keys were added
    with test_db.engine.connect() as conn:
        # Check that primary key constraints exist
        result = conn.execute(
            text(f"""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints 
            WHERE constraint_type = 'PRIMARY KEY' 
            AND table_schema = '{integration_settings.schema_name}'
        """)
        )
        pk_count = result.scalar()
        assert pk_count > 0, "Should have primary key constraints"

        # Check specific primary keys for key tables
        key_tables = ["person", "concept", "condition_occurrence", "drug_exposure"]
        for table in key_tables:
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints 
                WHERE constraint_type = 'PRIMARY KEY' 
                AND table_schema = '{integration_settings.schema_name}'
                AND table_name = '{table}'
            """)
            )
            pk_exists = result.scalar()
            assert pk_exists == 1, f"Table {table} should have exactly one primary key"


def test_add_indices_integration(
    test_db: PostgresDatabase, integration_settings: Settings
):
    """Integration test for adding indices."""
    # Create schema and tables
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Add indices
    test_db.add_indices()

    # Verify indices were added
    with test_db.engine.connect() as conn:
        # Check that indices exist
        result = conn.execute(
            text(f"""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE schemaname = '{integration_settings.schema_name}'
        """)
        )
        index_count = result.scalar()
        assert index_count > 0, "Should have indices"

        # Check specific indices for key tables
        key_indices = [
            ("person", "idx_person_id"),
            ("person", "idx_gender"),
            ("condition_occurrence", "idx_condition_person_id_1"),
            ("drug_exposure", "idx_drug_person_id_1"),
            ("measurement", "idx_measurement_person_id_1"),
            ("concept", "idx_concept_concept_id"),
        ]

        for table, index_name in key_indices:
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = '{integration_settings.schema_name}'
                AND tablename = '{table}'
                AND indexname = '{index_name}'
            """)
            )
            index_exists = result.scalar()
            assert (
                index_exists == 1
            ), f"Index {index_name} should exist on table {table}"


def test_add_constraints_integration(
    test_db: PostgresDatabase, integration_settings: Settings
):
    """Integration test for adding foreign key constraints."""
    # Arrange
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()
    test_db.add_primary_keys()

    # Act
    test_db.add_constraints()

    # Assert
    with test_db.engine.connect() as conn:
        # Check that foreign key constraints exist
        result = conn.execute(
            text(f"""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints 
            WHERE constraint_type = 'FOREIGN KEY' 
            AND table_schema = '{integration_settings.schema_name}'
        """)
        )
        fk_count = result.scalar()
        assert fk_count > 0, "Should have foreign key constraints"

        # Check specific foreign keys for key tables
        key_foreign_keys = [
            ("person", "fpk_person_gender_concept_id"),
            ("person", "fpk_person_race_concept_id"),
            ("condition_occurrence", "fpk_condition_occurrence_person_id"),
            ("drug_exposure", "fpk_drug_exposure_person_id"),
            ("measurement", "fpk_measurement_person_id"),
        ]

        for table, constraint_name in key_foreign_keys:
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints 
                WHERE constraint_type = 'FOREIGN KEY' 
                AND table_schema = '{integration_settings.schema_name}'
                AND table_name = '{table}'
                AND constraint_name = '{constraint_name}'
            """)
            )
            fk_exists = result.scalar()
            assert (
                fk_exists == 1
            ), f"Foreign key {constraint_name} should exist on table {table}"


def test_add_all_constraints_integration(
    test_db: PostgresDatabase, integration_settings: Settings
):
    """Integration test for adding all constraints (primary keys, indices, foreign keys)."""
    # Create schema and tables
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Add all constraints
    test_db.add_all_constraints()

    # Verify all types of constraints were added
    with test_db.engine.connect() as conn:
        # Check primary keys
        result = conn.execute(
            text(f"""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints 
            WHERE constraint_type = 'PRIMARY KEY' 
            AND table_schema = '{integration_settings.schema_name}'
        """)
        )
        pk_count = result.scalar()
        assert pk_count > 0, "Should have primary key constraints"

        # Check foreign keys
        result = conn.execute(
            text(f"""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints 
            WHERE constraint_type = 'FOREIGN KEY' 
            AND table_schema = '{integration_settings.schema_name}'
        """)
        )
        fk_count = result.scalar()
        assert fk_count > 0, "Should have foreign key constraints"

        # Check indices
        result = conn.execute(
            text(f"""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE schemaname = '{integration_settings.schema_name}'
        """)
        )
        index_count = result.scalar()
        assert index_count > 0, "Should have indices"

        # Verify specific constraint counts match expectations
        assert pk_count >= 25, f"Expected at least 25 primary keys, got {pk_count}"
        assert fk_count >= 100, f"Expected at least 100 foreign keys, got {fk_count}"
        assert index_count >= 50, f"Expected at least 50 indices, got {index_count}"


def test_load_synthetic_data_integration(
    test_db: PostgresDatabase, integration_settings: Settings
):
    """Integration test for loading synthetic data."""
    # Configure settings for synthetic 100 data
    integration_settings.synthetic = True
    integration_settings.synthetic_number = 100

    # Create schema and tables
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Load synthetic data
    test_db.load_data()

    # Verify data was loaded by checking row counts
    with test_db.engine.connect() as conn:
        # Check person table
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.person")
        )
        person_count = result.scalar()
        assert person_count == 99, f"Expected 99 persons, got {person_count}"

        # Check concept table
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.concept")
        )
        concept_count = result.scalar()
        assert concept_count > 0, "Concept table should have data"

        # Check condition_occurrence table
        result = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {integration_settings.schema_name}.condition_occurrence"
            )
        )
        condition_count = result.scalar()
        assert condition_count > 0, "Condition occurrence table should have data"

        # Check domain table
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.domain")
        )
        domain_count = result.scalar()
        assert domain_count > 0, "Domain table should have data"

        # Check drug_strength table
        result = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {integration_settings.schema_name}.drug_strength"
            )
        )
        drug_count = result.scalar()
        assert drug_count > 0, "Drug strength table should have data"

        # Check measurement table
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.measurement")
        )
        measurement_count = result.scalar()
        assert measurement_count > 0, "Measurement table should have data"

        # Check observation table
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.observation")
        )
        observation_count = result.scalar()
        assert observation_count > 0, "Observation table should have data"

        # Check relationship table
        result = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {integration_settings.schema_name}.relationship"
            )
        )
        relationship_count = result.scalar()
        assert relationship_count > 0, "Relationship table should have data"


def test_load_synthetic_data_sample_verification(
    test_db: PostgresDatabase, integration_settings: Settings
):
    """Integration test to verify sample data quality."""
    # Configure settings for synthetic 100 data
    integration_settings.synthetic = True
    integration_settings.synthetic_number = 100

    # Create schema and tables
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Load synthetic data
    test_db.load_data()

    # Verify sample data quality
    with test_db.engine.connect() as conn:
        # Check that person data looks reasonable
        result = conn.execute(
            text(f"""
            SELECT person_id, gender_concept_id, year_of_birth 
            FROM {integration_settings.schema_name}.person 
            LIMIT 5
        """)
        )
        persons = result.fetchall()
        assert len(persons) > 0, "Should have person data"

        for person in persons:
            assert person.person_id is not None, "Person ID should not be null"
            assert (
                person.gender_concept_id is not None
            ), "Gender concept ID should not be null"
            assert (
                1900 <= person.year_of_birth <= 2024
            ), f"Year of birth {person.year_of_birth} should be reasonable"

        # Check that concept data looks reasonable
        result = conn.execute(
            text(f"""
            SELECT concept_id, concept_name, domain_id 
            FROM {integration_settings.schema_name}.concept 
            LIMIT 5
        """)
        )
        concepts = result.fetchall()
        assert len(concepts) > 0, "Should have concept data"

        for concept in concepts:
            assert concept.concept_id is not None, "Concept ID should not be null"
            assert concept.concept_name is not None, "Concept name should not be null"
            assert concept.domain_id is not None, "Domain ID should not be null"


def test_full_pipeline_integration(
    test_db: PostgresDatabase, integration_settings: Settings
):
    """Integration test for the full pipeline: schema, tables, data, constraints."""
    # Configure settings for synthetic 100 data
    integration_settings.synthetic = True
    integration_settings.synthetic_number = 100

    # Full pipeline: schema -> tables -> data -> constraints
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()
    test_db.load_data()
    test_db.add_all_constraints()

    # Verify everything worked
    with test_db.engine.connect() as conn:
        # Check data exists
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.person")
        )
        person_count = result.scalar()
        assert person_count == 99, f"Expected 99 persons, got {person_count}"

        # Check constraints exist (primary keys)
        result = conn.execute(
            text(f"""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints 
            WHERE constraint_type = 'PRIMARY KEY' 
            AND table_schema = '{integration_settings.schema_name}'
        """)
        )
        pk_count = result.scalar()
        assert pk_count > 0, "Should have primary key constraints"

        # Check indexes exist
        result = conn.execute(
            text(f"""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE schemaname = '{integration_settings.schema_name}'
        """)
        )
        index_count = result.scalar()
        assert index_count > 0, "Should have indexes"


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
