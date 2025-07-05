import pytest
from sqlalchemy import inspect, text

from omop_lite.db.postgres import PostgresDatabase
from omop_lite.db.sqlserver import SQLServerDatabase
from omop_lite.settings import Settings


@pytest.fixture
def test_db(integration_settings, db_class):
    """Create a test database connection."""
    db = db_class(integration_settings)
    yield db
    try:
        db.drop_all(integration_settings.schema_name)
    except Exception:
        pass


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_create_schema_integration(test_db, integration_settings: Settings, db_class):
    """Integration test for schema creation."""
    # Arrange
    assert not test_db.schema_exists(integration_settings.schema_name)

    # Act
    test_db.create_schema(integration_settings.schema_name)

    # Assert
    assert test_db.schema_exists(integration_settings.schema_name)
    inspector = inspect(test_db.engine)
    schemas = inspector.get_schema_names()
    assert integration_settings.schema_name in schemas


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_create_tables_integration(test_db, integration_settings: Settings, db_class):
    """Integration test for table creation."""
    # Arrange
    test_db.create_schema(integration_settings.schema_name)

    # Act
    test_db.create_tables()

    # Assert
    inspector = inspect(test_db.engine)
    tables = inspector.get_table_names(schema=integration_settings.schema_name)

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

    assert len(tables) == 39, f"Expected 39 tables, got {len(tables)}"

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


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_add_primary_keys_integration(
    test_db, integration_settings: Settings, db_class
):
    """Integration test for adding primary keys."""
    # Arrange
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Act
    test_db.add_primary_keys()

    # Assert
    with test_db.engine.connect() as conn:
        if db_class == PostgresDatabase:
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints 
                WHERE constraint_type = 'PRIMARY KEY' 
                AND table_schema = '{integration_settings.schema_name}'
            """)
            )
        else:  # SQL Server
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


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_add_indices_integration(test_db, integration_settings: Settings, db_class):
    """Integration test for adding indices."""
    # Arrange
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Act
    test_db.add_indices()

    # Assert
    with test_db.engine.connect() as conn:
        if db_class == PostgresDatabase:
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = '{integration_settings.schema_name}'
            """)
            )
        else:  # SQL Server
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM sys.indexes i
                JOIN sys.tables t ON i.object_id = t.object_id
                JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE s.name = '{integration_settings.schema_name}'
                AND i.is_hypothetical = 0
            """)
            )
        index_count = result.scalar()
        assert index_count > 0, "Should have indices"

        if db_class == PostgresDatabase:
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


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_add_constraints_integration(test_db, integration_settings: Settings, db_class):
    """Integration test for adding foreign key constraints."""
    # Arrange
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()
    test_db.add_primary_keys()

    # Act
    test_db.add_constraints()

    # Assert
    with test_db.engine.connect() as conn:
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


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_add_all_constraints_integration(
    test_db, integration_settings: Settings, db_class
):
    """Integration test for adding all constraints (primary keys, indices, foreign keys)."""
    # Arrange
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Act
    test_db.add_all_constraints()

    # Assert
    with test_db.engine.connect() as conn:
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

        if db_class == PostgresDatabase:
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = '{integration_settings.schema_name}'
            """)
            )
        else:  # SQL Server
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM sys.indexes i
                JOIN sys.tables t ON i.object_id = t.object_id
                JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE s.name = '{integration_settings.schema_name}'
                AND i.is_hypothetical = 0
            """)
            )
        index_count = result.scalar()
        assert index_count > 0, "Should have indices"

        assert pk_count >= 25, f"Expected at least 25 primary keys, got {pk_count}"
        assert fk_count >= 100, f"Expected at least 100 foreign keys, got {fk_count}"
        assert index_count >= 50, f"Expected at least 50 indices, got {index_count}"


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_load_synthetic_data_integration(
    test_db, integration_settings: Settings, db_class
):
    """Integration test for loading synthetic data."""
    # Arrange
    integration_settings.synthetic = True
    integration_settings.synthetic_number = 100
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Act
    test_db.load_data()

    # Assert
    with test_db.engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.person")
        )
        person_count = result.scalar()
        assert person_count == 99, f"Expected 99 persons, got {person_count}"

        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.concept")
        )
        concept_count = result.scalar()
        assert concept_count > 0, "Concept table should have data"

        result = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {integration_settings.schema_name}.condition_occurrence"
            )
        )
        condition_count = result.scalar()
        assert condition_count > 0, "Condition occurrence table should have data"

        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.domain")
        )
        domain_count = result.scalar()
        assert domain_count > 0, "Domain table should have data"

        result = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {integration_settings.schema_name}.drug_strength"
            )
        )
        drug_count = result.scalar()
        assert drug_count > 0, "Drug strength table should have data"

        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.measurement")
        )
        measurement_count = result.scalar()
        assert measurement_count > 0, "Measurement table should have data"

        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.observation")
        )
        observation_count = result.scalar()
        assert observation_count > 0, "Observation table should have data"

        result = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {integration_settings.schema_name}.relationship"
            )
        )
        relationship_count = result.scalar()
        assert relationship_count > 0, "Relationship table should have data"


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_load_synthetic_data_sample_verification(
    test_db, integration_settings: Settings, db_class
):
    """Integration test to verify sample data quality."""
    # Arrange
    integration_settings.synthetic = True
    integration_settings.synthetic_number = 100
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Act
    test_db.load_data()

    # Assert
    with test_db.engine.connect() as conn:
        result = conn.execute(
            text(f"""
            SELECT person_id, gender_concept_id, year_of_birth 
            FROM {integration_settings.schema_name}.person 
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

        result = conn.execute(
            text(f"""
            SELECT concept_id, concept_name, domain_id 
            FROM {integration_settings.schema_name}.concept 
        """)
        )
        concepts = result.fetchall()
        assert len(concepts) > 0, "Should have concept data"

        for concept in concepts:
            assert concept.concept_id is not None, "Concept ID should not be null"
            assert concept.concept_name is not None, "Concept name should not be null"
            assert concept.domain_id is not None, "Domain ID should not be null"


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_full_pipeline_integration(test_db, integration_settings: Settings, db_class):
    """Integration test for the full pipeline: schema, tables, data, constraints."""
    # Arrange
    integration_settings.synthetic = True
    integration_settings.synthetic_number = 100

    # Act
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()
    test_db.load_data()
    test_db.add_all_constraints()

    # Assert
    with test_db.engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {integration_settings.schema_name}.person")
        )
        person_count = result.scalar()
        assert person_count == 99, f"Expected 99 persons, got {person_count}"

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

        if db_class == PostgresDatabase:
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = '{integration_settings.schema_name}'
            """)
            )
        else:  # SQL Server
            result = conn.execute(
                text(f"""
                SELECT COUNT(*) 
                FROM sys.indexes i
                JOIN sys.tables t ON i.object_id = t.object_id
                JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE s.name = '{integration_settings.schema_name}'
                AND i.is_hypothetical = 0
            """)
            )
        index_count = result.scalar()
        assert index_count > 0, "Should have indexes"


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_create_tables_twice_integration(
    test_db, integration_settings: Settings, db_class
):
    """Test that creating tables twice doesn't fail."""
    # Arrange
    test_db.create_schema(integration_settings.schema_name)
    test_db.create_tables()

    # Act
    test_db.create_tables()

    # Assert
    inspector = inspect(test_db.engine)
    tables = inspector.get_table_names(schema=integration_settings.schema_name)
    assert len(tables) == 39


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_drop_schema_integration(test_db, integration_settings: Settings, db_class):
    """Integration test for schema dropping."""
    # Arrange
    test_db.create_schema(integration_settings.schema_name)
    assert test_db.schema_exists(integration_settings.schema_name)

    # Act
    test_db.drop_schema(integration_settings.schema_name)

    # Assert
    assert not test_db.schema_exists(integration_settings.schema_name)
    inspector = inspect(test_db.engine)
    schemas = inspector.get_schema_names()
    assert integration_settings.schema_name not in schemas


@pytest.mark.parametrize("db_class", [PostgresDatabase, SQLServerDatabase])
def test_schema_exists_integration(test_db, integration_settings: Settings, db_class):
    """Integration test for schema existence checking."""
    # Arrange & Act & Assert
    assert not test_db.schema_exists("non_existent_schema")

    test_db.create_schema(integration_settings.schema_name)
    assert test_db.schema_exists(integration_settings.schema_name)

    test_db.drop_schema(integration_settings.schema_name)
    assert not test_db.schema_exists(integration_settings.schema_name)
