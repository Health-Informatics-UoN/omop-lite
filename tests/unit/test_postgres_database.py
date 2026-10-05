import pytest
from unittest.mock import Mock, mock_open, patch
from pathlib import Path

from omop_lite.settings import Settings
from omop_lite.db.postgres import PostgresDatabase


@pytest.fixture
def postgres_settings():
    """Create test settings for PostgreSQL."""
    return Settings(
        db_host="localhost",
        db_port=5432,
        db_user="postgres",
        db_password="password",
        db_name="omop",
        schema_name="cdm",
        dialect="postgresql",
    )


@pytest.fixture
def mock_postgres_db(postgres_settings):
    """Create a PostgresDatabase instance with all dependencies mocked."""
    with (
        patch("omop_lite.db.postgres.create_engine") as mock_create_engine,
        patch("omop_lite.db.postgres.files") as mock_files,
        patch("omop_lite.db.postgres.MetaData") as mock_metadata,
    ):
        # Mock the engine and metadata
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = PostgresDatabase(postgres_settings)
        return db


@patch("omop_lite.db.postgres.create_engine")
@patch("omop_lite.db.postgres.files")
@patch("omop_lite.db.postgres.MetaData")
def test_db_url_construction(
    mock_metadata, mock_files, mock_create_engine, postgres_settings
):
    """Test that the database URL is constructed correctly."""
    # Mock the engine and metadata
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine
    mock_files.return_value = Mock()
    mock_metadata.return_value = Mock()

    db = PostgresDatabase(postgres_settings)

    expected_url = "postgresql+psycopg2://postgres:password@localhost:5432/omop"
    assert db.db_url == expected_url


def test_db_url_with_different_credentials():
    """Test database URL with different credentials."""
    settings = Settings(
        db_host="db.example.com",
        db_port=5433,
        db_user="myuser",
        db_password="mypass",
        db_name="mydb",
        dialect="postgresql",
    )

    with (
        patch("omop_lite.db.postgres.create_engine") as mock_create_engine,
        patch("omop_lite.db.postgres.files") as mock_files,
        patch("omop_lite.db.postgres.MetaData") as mock_metadata,
    ):
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = PostgresDatabase(settings)

        expected_url = "postgresql+psycopg2://myuser:mypass@db.example.com:5433/mydb"
        assert db.db_url == expected_url


def test_create_schema_issues_create_schema_sql(mock_postgres_db):
    """create_schema must actually run CREATE SCHEMA IF NOT EXISTS, quoted
    to preserve case (see #97)."""
    mock_connection = Mock()
    mock_postgres_db.engine.connect.return_value.__enter__ = Mock(
        return_value=mock_connection
    )
    mock_postgres_db.engine.connect.return_value.__exit__ = Mock(return_value=False)

    mock_postgres_db.create_schema("test_schema")

    executed_sql = str(mock_connection.execute.call_args[0][0])
    assert executed_sql == 'CREATE SCHEMA IF NOT EXISTS "test_schema"'
    mock_connection.commit.assert_called_once()


def test_fts_disabled_is_a_noop(mock_postgres_db):
    """_add_full_text_search must do nothing when fts_create is disabled."""
    mock_postgres_db.settings.fts_create = False
    with patch.object(mock_postgres_db, "_execute_sql_file") as mock_execute:
        mock_postgres_db._add_full_text_search()
    mock_execute.assert_not_called()


def test_fts_enabled_runs_both_sql_files(mock_postgres_db):
    """_add_full_text_search must run the column and index SQL files when
    fts_create is enabled.

    _execute_sql_file is mocked here because fts.sql/fts_index.sql don't
    actually exist in the repo yet (a separate, already-flagged bug) -
    this test is about whether add_constraints wires FTS up correctly,
    not about those files' content.
    """
    mock_postgres_db.settings.fts_create = True
    with patch.object(mock_postgres_db, "_execute_sql_file") as mock_execute:
        mock_postgres_db._add_full_text_search()
    assert mock_execute.call_count == 2


def test_bulk_load_quotes_mixed_case_schema(mock_postgres_db):
    """_bulk_load must quote the schema name in the COPY statement.

    Postgres folds an unquoted mixed-case schema name to lower-case, which
    would silently divert the COPY into a different (likely non-existent)
    schema than the one create_schema actually created - see #97.
    """
    mock_postgres_db.settings.schema_name = "MixedCase"
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_postgres_db.engine.raw_connection.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    with patch("builtins.open", mock_open()):
        mock_postgres_db._bulk_load("person", Path("/data/person.csv"))

    executed_sql = mock_cursor.copy_expert.call_args[0][0]
    assert executed_sql.startswith('COPY "MixedCase".person')


def test_settings_validation():
    """Test that settings are properly validated."""
    # Test valid settings
    valid_settings = Settings(
        db_host="localhost",
        db_port=5432,
        db_user="user",
        db_password="pass",
        db_name="db",
        dialect="postgresql",
    )

    assert valid_settings.db_host == "localhost"
    assert valid_settings.db_port == 5432
    assert valid_settings.dialect == "postgresql"

    # Test that invalid dialect raises error
    with pytest.raises(ValueError):
        Settings(dialect="invalid")


def test_get_delimiter_and_quote_synthetic_1000(mock_postgres_db):
    """Synthetic 1000/1001 data is comma-delimited with '\"' quoting."""
    mock_postgres_db.settings.synthetic = True
    mock_postgres_db.settings.synthetic_number = 1000
    assert mock_postgres_db._get_delimiter() == ","
    assert mock_postgres_db._get_quote() == '"'


def test_get_delimiter_and_quote_real_data(mock_postgres_db):
    """Non-synthetic data uses the configured delimiter and no quote char."""
    mock_postgres_db.settings.synthetic = False
    mock_postgres_db.settings.delimiter = "|"
    assert mock_postgres_db._get_delimiter() == "|"
    assert mock_postgres_db._get_quote() == "\b"


def test_schema_name_handling():
    """Test schema name handling."""
    # Test default schema
    default_settings = Settings()
    assert default_settings.schema_name == "public"

    # Test custom schema
    custom_settings = Settings(schema_name="cdm")
    assert custom_settings.schema_name == "cdm"


def test_omop_tables_list(mock_postgres_db):
    """Test that the OMOP tables list is correct."""
    # Test that all expected tables are present
    expected_tables = [
        "PERSON",
        "CONCEPT",
        "CONDITION_OCCURRENCE",
        "DRUG_EXPOSURE",
        "MEASUREMENT",
        "OBSERVATION",
    ]

    for table in expected_tables:
        assert table in mock_postgres_db.omop_tables

    # Test total count
    assert len(mock_postgres_db.omop_tables) == 39
