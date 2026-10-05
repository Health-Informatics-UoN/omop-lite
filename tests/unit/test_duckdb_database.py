from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from omop_lite.db.base import SqlBatchResult
from omop_lite.db.duckdb import DuckDBDatabase
from omop_lite.settings import Settings


@pytest.fixture
def duckdb_settings():
    """Create test settings for DuckDB."""
    return Settings(
        db_name="omop.duckdb",
        schema_name="cdm",
        dialect="duckdb",
    )


@pytest.fixture
def mock_duckdb_db(duckdb_settings):
    """Create a DuckDBDatabase instance with all dependencies mocked."""
    with (
        patch("omop_lite.db.duckdb.create_engine") as mock_create_engine,
        patch("omop_lite.db.duckdb.files") as mock_files,
        patch("omop_lite.db.duckdb.MetaData") as mock_metadata,
    ):
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = DuckDBDatabase(duckdb_settings)
        return db


def test_db_url_construction(duckdb_settings):
    """Test that the database URL is the file path, not a server connection."""
    with (
        patch("omop_lite.db.duckdb.create_engine") as mock_create_engine,
        patch("omop_lite.db.duckdb.files") as mock_files,
        patch("omop_lite.db.duckdb.MetaData") as mock_metadata,
    ):
        mock_create_engine.return_value = Mock()
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = DuckDBDatabase(duckdb_settings)

        assert db.db_url == "duckdb:///omop.duckdb"


def test_db_url_with_absolute_path(tmp_path):
    """Test database URL construction with an absolute db_name path."""
    db_file = tmp_path / "data" / "omop.duckdb"
    settings = Settings(db_name=str(db_file), schema_name="cdm", dialect="duckdb")

    with (
        patch("omop_lite.db.duckdb.create_engine") as mock_create_engine,
        patch("omop_lite.db.duckdb.files") as mock_files,
        patch("omop_lite.db.duckdb.MetaData") as mock_metadata,
    ):
        mock_create_engine.return_value = Mock()
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = DuckDBDatabase(settings)

        assert db.db_url == f"duckdb:///{db_file}"
        # The parent directory should have been created for the output file.
        assert db_file.parent.is_dir()


def test_schema_exists_true(mock_duckdb_db):
    """schema_exists should query duckdb_schemas() directly, not reflection."""
    mock_connection = Mock()
    mock_connection.execute.return_value.first.return_value = (1,)
    mock_duckdb_db.engine.connect.return_value.__enter__ = Mock(
        return_value=mock_connection
    )
    mock_duckdb_db.engine.connect.return_value.__exit__ = Mock(return_value=False)

    assert mock_duckdb_db.schema_exists("cdm") is True
    args, _ = mock_connection.execute.call_args
    assert "duckdb_schemas()" in str(args[0])


def test_tables_exist_true(mock_duckdb_db):
    """tables_exist should query duckdb_tables() directly, not reflection."""
    mock_connection = Mock()
    mock_connection.execute.return_value.first.return_value = (1,)
    mock_duckdb_db.engine.connect.return_value.__enter__ = Mock(
        return_value=mock_connection
    )
    mock_duckdb_db.engine.connect.return_value.__exit__ = Mock(return_value=False)

    assert mock_duckdb_db.tables_exist("cdm") is True
    args, _ = mock_connection.execute.call_args
    assert "duckdb_tables()" in str(args[0])


def test_tables_exist_false(mock_duckdb_db):
    """tables_exist should return False when no matching table is found."""
    mock_connection = Mock()
    mock_connection.execute.return_value.first.return_value = None
    mock_duckdb_db.engine.connect.return_value.__enter__ = Mock(
        return_value=mock_connection
    )
    mock_duckdb_db.engine.connect.return_value.__exit__ = Mock(return_value=False)

    assert mock_duckdb_db.tables_exist("cdm") is False


def test_schema_exists_false(mock_duckdb_db):
    """schema_exists should return False when no matching schema is found."""
    mock_connection = Mock()
    mock_connection.execute.return_value.first.return_value = None
    mock_duckdb_db.engine.connect.return_value.__enter__ = Mock(
        return_value=mock_connection
    )
    mock_duckdb_db.engine.connect.return_value.__exit__ = Mock(return_value=False)

    assert mock_duckdb_db.schema_exists("missing") is False


def test_refresh_metadata_is_noop(mock_duckdb_db):
    """refresh_metadata should not touch the engine (reflection is unreliable)."""
    mock_duckdb_db.refresh_metadata()
    mock_duckdb_db.engine.connect.assert_not_called()


def test_drop_tables_issues_drop_statements(mock_duckdb_db):
    """drop_tables should DROP each OMOP table directly, without reflection."""
    mock_connection = Mock()
    mock_duckdb_db.engine.connect.return_value.__enter__ = Mock(
        return_value=mock_connection
    )
    mock_duckdb_db.engine.connect.return_value.__exit__ = Mock(return_value=False)

    mock_duckdb_db.drop_tables()

    assert mock_connection.execute.call_count == len(mock_duckdb_db.omop_tables)
    mock_connection.commit.assert_called_once()


def test_add_constraints_warns_and_delegates(mock_duckdb_db, caplog):
    """add_constraints should warn about skipped FKs, then run the (empty) SQL file."""
    with patch.object(mock_duckdb_db, "_apply_sql_statements") as mock_apply:
        mock_apply.return_value = SqlBatchResult(succeeded=0, failed=0)
        result = mock_duckdb_db.add_constraints()

    mock_apply.assert_called_once()
    assert "not supported by DuckDB" in caplog.text
    assert result == SqlBatchResult(succeeded=0, failed=0)


def test_bulk_load_quotes_mixed_case_schema(mock_duckdb_db):
    """_bulk_load must quote the schema name in the COPY statement.

    DuckDB folds an unquoted mixed-case schema name to lower-case, which
    would silently divert the COPY into a different (likely non-existent)
    schema than the one create_schema actually created - see #97.
    """
    mock_duckdb_db.settings.schema_name = "MixedCase"
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_duckdb_db.engine.raw_connection.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    mock_duckdb_db._bulk_load("person", Path("/data/person.csv"))

    executed_sql = mock_cursor.execute.call_args[0][0]
    assert executed_sql.startswith('COPY "MixedCase".person')


def test_drop_tables_quotes_mixed_case_schema(mock_duckdb_db):
    """drop_tables must quote the schema name in the DROP TABLE statement."""
    mock_duckdb_db.settings.schema_name = "MixedCase"
    mock_connection = Mock()
    mock_duckdb_db.engine.connect.return_value.__enter__ = Mock(
        return_value=mock_connection
    )
    mock_duckdb_db.engine.connect.return_value.__exit__ = Mock(return_value=False)

    mock_duckdb_db.drop_tables()

    executed_sql = str(mock_connection.execute.call_args_list[0][0][0])
    assert '"MixedCase".' in executed_sql


def test_omop_tables_list(mock_duckdb_db):
    """Test that the OMOP tables list is correct for the duckdb dialect too."""
    expected_tables = [
        "PERSON",
        "CONCEPT",
        "CONDITION_OCCURRENCE",
        "DRUG_EXPOSURE",
        "MEASUREMENT",
        "OBSERVATION",
    ]

    for table in expected_tables:
        assert table in mock_duckdb_db.omop_tables

    assert len(mock_duckdb_db.omop_tables) == 39


def test_dialect_setting_accepts_duckdb():
    """Settings should accept 'duckdb' as a valid dialect."""
    settings = Settings(dialect="duckdb")
    assert settings.dialect == "duckdb"
