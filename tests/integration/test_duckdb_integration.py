"""Integration tests for the DuckDB dialect.

Unlike PostgreSQL/SQL Server, these need no external service - DuckDB is
file-based, so each test just gets a fresh file under `tmp_path`. This is
also why these live in a dedicated file rather than being folded into
`test_database_integration.py`'s `[PostgresDatabase, SQLServerDatabase]`
parametrization: that file leans on SQLAlchemy's `inspect()`/reflection for
assertions, which is unreliable for DuckDB (see `DuckDBDatabase`'s docstring),
and asserts foreign key constraints exist, which DuckDB does not support
adding after table creation - both would need per-test special-casing rather
than a clean three-way parametrize.
"""

import pytest
from sqlalchemy import text

from omop_lite.db.duckdb import DuckDBDatabase
from omop_lite.settings import Settings


@pytest.fixture
def duckdb_settings(tmp_path):
    """Create settings for a fresh DuckDB file per test."""
    return Settings(
        db_name=str(tmp_path / "omop.duckdb"),
        schema_name="test_cdm",
        dialect="duckdb",
    )


@pytest.fixture
def test_db(duckdb_settings: Settings):
    """Create a test database connection."""
    db = DuckDBDatabase(duckdb_settings)
    yield db
    try:
        db.drop_all(duckdb_settings.schema_name)
    except Exception:
        pass


def _table_names(test_db: DuckDBDatabase, schema_name: str) -> set[str]:
    with test_db.engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema_name"
            ),
            {"schema_name": schema_name},
        )
        return {row[0] for row in result}


def test_create_schema_integration(test_db: DuckDBDatabase, duckdb_settings: Settings):
    """Integration test for schema creation."""
    assert not test_db.schema_exists(duckdb_settings.schema_name)

    test_db.create_schema(duckdb_settings.schema_name)

    assert test_db.schema_exists(duckdb_settings.schema_name)


def test_create_tables_integration(test_db: DuckDBDatabase, duckdb_settings: Settings):
    """Integration test for table creation."""
    test_db.create_schema(duckdb_settings.schema_name)

    test_db.create_tables()

    tables = _table_names(test_db, duckdb_settings.schema_name)
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


def test_add_primary_keys_integration(
    test_db: DuckDBDatabase, duckdb_settings: Settings
):
    """Integration test for adding primary keys."""
    test_db.create_schema(duckdb_settings.schema_name)
    test_db.create_tables()

    test_db.add_primary_keys()

    with test_db.engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM duckdb_constraints() "
                "WHERE schema_name = :schema_name AND constraint_type = 'PRIMARY KEY'"
            ),
            {"schema_name": duckdb_settings.schema_name},
        )
        assert result.scalar() > 0, "Should have primary key constraints"

        for table in ["person", "concept", "condition_occurrence", "drug_exposure"]:
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM duckdb_constraints() "
                    "WHERE schema_name = :schema_name AND table_name = :table_name "
                    "AND constraint_type = 'PRIMARY KEY'"
                ),
                {"schema_name": duckdb_settings.schema_name, "table_name": table},
            )
            assert result.scalar() == 1, f"Table {table} should have a primary key"


def test_add_indices_integration(test_db: DuckDBDatabase, duckdb_settings: Settings):
    """Integration test for adding indices."""
    test_db.create_schema(duckdb_settings.schema_name)
    test_db.create_tables()

    test_db.add_indices()

    with test_db.engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM duckdb_indexes() WHERE schema_name = :schema_name"
            ),
            {"schema_name": duckdb_settings.schema_name},
        )
        assert result.scalar() > 0, "Should have indices"


def test_add_constraints_integration_skips_foreign_keys(
    test_db: DuckDBDatabase, duckdb_settings: Settings
):
    """Foreign keys cannot be added after table creation in DuckDB, so
    add_constraints() is a documented no-op for this dialect - it should run
    without error and leave zero foreign keys behind."""
    test_db.create_schema(duckdb_settings.schema_name)
    test_db.create_tables()
    test_db.add_primary_keys()

    test_db.add_constraints()

    with test_db.engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM duckdb_constraints() "
                "WHERE schema_name = :schema_name AND constraint_type = 'FOREIGN KEY'"
            ),
            {"schema_name": duckdb_settings.schema_name},
        )
        assert result.scalar() == 0


def test_add_all_constraints_integration(
    test_db: DuckDBDatabase, duckdb_settings: Settings
):
    """Integration test for adding all constraints (primary keys and indices)."""
    test_db.create_schema(duckdb_settings.schema_name)
    test_db.create_tables()

    test_db.add_all_constraints()

    with test_db.engine.connect() as conn:
        pk_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM duckdb_constraints() "
                "WHERE schema_name = :schema_name AND constraint_type = 'PRIMARY KEY'"
            ),
            {"schema_name": duckdb_settings.schema_name},
        ).scalar()
        index_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM duckdb_indexes() WHERE schema_name = :schema_name"
            ),
            {"schema_name": duckdb_settings.schema_name},
        ).scalar()

        assert pk_count >= 25, f"Expected at least 25 primary keys, got {pk_count}"
        assert index_count >= 50, f"Expected at least 50 indices, got {index_count}"


def test_load_synthetic_data_integration(
    test_db: DuckDBDatabase, duckdb_settings: Settings
):
    """Integration test for loading synthetic data."""
    duckdb_settings.synthetic = True
    duckdb_settings.synthetic_number = 100
    test_db.create_schema(duckdb_settings.schema_name)
    test_db.create_tables()

    test_db.load_data()

    with test_db.engine.connect() as conn:
        person_count = conn.execute(
            text(f"SELECT COUNT(*) FROM {duckdb_settings.schema_name}.person")
        ).scalar()
        assert person_count == 99, f"Expected 99 persons, got {person_count}"

        concept_count = conn.execute(
            text(f"SELECT COUNT(*) FROM {duckdb_settings.schema_name}.concept")
        ).scalar()
        assert concept_count > 0, "Concept table should have data"


def test_full_pipeline_integration(test_db: DuckDBDatabase, duckdb_settings: Settings):
    """Integration test for the full pipeline: schema, tables, data, constraints."""
    duckdb_settings.synthetic = True
    duckdb_settings.synthetic_number = 100

    test_db.create_schema(duckdb_settings.schema_name)
    test_db.create_tables()
    test_db.load_data()
    test_db.add_all_constraints()

    with test_db.engine.connect() as conn:
        person_count = conn.execute(
            text(f"SELECT COUNT(*) FROM {duckdb_settings.schema_name}.person")
        ).scalar()
        assert person_count == 99, f"Expected 99 persons, got {person_count}"

        pk_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM duckdb_constraints() "
                "WHERE schema_name = :schema_name AND constraint_type = 'PRIMARY KEY'"
            ),
            {"schema_name": duckdb_settings.schema_name},
        ).scalar()
        assert pk_count > 0, "Should have primary key constraints"


def test_create_tables_twice_integration(
    test_db: DuckDBDatabase, duckdb_settings: Settings
):
    """Test that creating tables twice doesn't fail."""
    test_db.create_schema(duckdb_settings.schema_name)
    test_db.create_tables()

    test_db.create_tables()

    tables = _table_names(test_db, duckdb_settings.schema_name)
    assert len(tables) == 39


def test_drop_schema_integration(test_db: DuckDBDatabase, duckdb_settings: Settings):
    """Integration test for schema dropping."""
    test_db.create_schema(duckdb_settings.schema_name)
    assert test_db.schema_exists(duckdb_settings.schema_name)

    test_db.drop_schema(duckdb_settings.schema_name)

    assert not test_db.schema_exists(duckdb_settings.schema_name)


def test_drop_tables_integration(test_db: DuckDBDatabase, duckdb_settings: Settings):
    """Integration test for dropping tables without reflected metadata."""
    test_db.create_schema(duckdb_settings.schema_name)
    test_db.create_tables()
    assert len(_table_names(test_db, duckdb_settings.schema_name)) == 39

    test_db.drop_tables()

    assert _table_names(test_db, duckdb_settings.schema_name) == set()


def test_schema_exists_integration(test_db: DuckDBDatabase, duckdb_settings: Settings):
    """Integration test for schema existence checking."""
    assert not test_db.schema_exists("non_existent_schema")

    test_db.create_schema(duckdb_settings.schema_name)
    assert test_db.schema_exists(duckdb_settings.schema_name)

    test_db.drop_schema(duckdb_settings.schema_name)
    assert not test_db.schema_exists(duckdb_settings.schema_name)
