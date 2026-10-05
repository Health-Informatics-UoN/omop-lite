import pytest
from unittest.mock import Mock, mock_open, patch
from pathlib import Path

from omop_lite.settings import Settings
from omop_lite.db.sqlserver import SQLServerDatabase


@pytest.fixture
def sqlserver_settings():
    """Create test settings for SQL Server."""
    return Settings(
        db_host="localhost",
        db_port=1433,
        db_user="sa",
        db_password="password",
        db_name="omop",
        schema_name="cdm",
        dialect="mssql",
    )


@pytest.fixture
def mock_sqlserver_db(sqlserver_settings):
    """Create a SQLServerDatabase instance with all dependencies mocked."""
    with (
        patch("omop_lite.db.sqlserver.create_engine") as mock_create_engine,
        patch("omop_lite.db.sqlserver.files") as mock_files,
        patch("omop_lite.db.sqlserver.MetaData") as mock_metadata,
    ):
        # Mock the engine and metadata
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = SQLServerDatabase(sqlserver_settings)
        return db


@patch("omop_lite.db.sqlserver.create_engine")
@patch("omop_lite.db.sqlserver.files")
@patch("omop_lite.db.sqlserver.MetaData")
def test_db_url_construction(
    mock_metadata, mock_files, mock_create_engine, sqlserver_settings
):
    """Test that the database URL is constructed correctly."""
    # Mock the engine and metadata
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine
    mock_files.return_value = Mock()
    mock_metadata.return_value = Mock()

    db = SQLServerDatabase(sqlserver_settings)

    expected_url = "mssql+pyodbc://sa:password@localhost:1433/omop?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
    assert db.db_url == expected_url


def test_db_url_with_different_credentials():
    """Test database URL with different credentials."""
    settings = Settings(
        db_host="db.example.com",
        db_port=1434,
        db_user="myuser",
        db_password="mypass",
        db_name="mydb",
        dialect="mssql",
    )

    with (
        patch("omop_lite.db.sqlserver.create_engine") as mock_create_engine,
        patch("omop_lite.db.sqlserver.files") as mock_files,
        patch("omop_lite.db.sqlserver.MetaData") as mock_metadata,
    ):
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = SQLServerDatabase(settings)

        expected_url = "mssql+pyodbc://myuser:mypass@db.example.com:1434/mydb?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
        assert db.db_url == expected_url


def test_create_schema_issues_create_schema_sql(mock_sqlserver_db):
    """create_schema must actually run the guarded CREATE SCHEMA statement,
    bracket-quoted to preserve case (see #97)."""
    mock_connection = Mock()
    mock_sqlserver_db.engine.connect.return_value.__enter__ = Mock(
        return_value=mock_connection
    )
    mock_sqlserver_db.engine.connect.return_value.__exit__ = Mock(return_value=False)

    mock_sqlserver_db.create_schema("test_schema")

    executed_sql = str(mock_connection.execute.call_args[0][0])
    assert "CREATE SCHEMA [test_schema]" in executed_sql
    assert "IF NOT EXISTS" in executed_sql
    mock_connection.commit.assert_called_once()


def test_bulk_load_quotes_mixed_case_schema(mock_sqlserver_db):
    """_bulk_load must bracket-quote the schema name in the INSERT
    statement, for consistency with create_schema (see #97)."""
    mock_sqlserver_db.settings.schema_name = "MixedCase"
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_sqlserver_db.engine.raw_connection.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    csv_data = "id\tname\tvalue\n1\ttest\t42\n"
    with patch("builtins.open", mock_open(read_data=csv_data)):
        mock_sqlserver_db._bulk_load("person", Path("/data/person.csv"))

    executed_sql = mock_cursor.execute.call_args[0][0]
    assert executed_sql.startswith("INSERT INTO [MixedCase].[person]")


def test_settings_validation():
    """Test that settings are properly validated."""
    # Test valid settings
    valid_settings = Settings(
        db_host="localhost",
        db_port=1433,
        db_user="user",
        db_password="pass",
        db_name="db",
        dialect="mssql",
    )

    assert valid_settings.db_host == "localhost"
    assert valid_settings.db_port == 1433
    assert valid_settings.dialect == "mssql"

    # Test that invalid dialect raises error
    with pytest.raises(ValueError):
        Settings(dialect="invalid")


def test_get_delimiter_and_quote_synthetic_1000(mock_sqlserver_db):
    """Synthetic 1000/1001 data is comma-delimited with '\"' quoting."""
    mock_sqlserver_db.settings.synthetic = True
    mock_sqlserver_db.settings.synthetic_number = 1000
    assert mock_sqlserver_db._get_delimiter() == ","
    assert mock_sqlserver_db._get_quote() == '"'


def test_get_delimiter_and_quote_real_data(mock_sqlserver_db):
    """Non-synthetic data uses the configured delimiter and no quote char."""
    mock_sqlserver_db.settings.synthetic = False
    mock_sqlserver_db.settings.delimiter = "|"
    assert mock_sqlserver_db._get_delimiter() == "|"
    assert mock_sqlserver_db._get_quote() == "\b"


def test_schema_name_handling():
    """Test schema name handling."""
    # Test default schema
    default_settings = Settings()
    assert default_settings.schema_name == "public"

    # Test custom schema
    custom_settings = Settings(schema_name="cdm")
    assert custom_settings.schema_name == "cdm"


def test_omop_tables_list(mock_sqlserver_db):
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
        assert table in mock_sqlserver_db.omop_tables

    # Test total count
    assert len(mock_sqlserver_db.omop_tables) == 39


def test_bulk_load_builds_insert_and_pads_trims_rows(mock_sqlserver_db):
    """_bulk_load must bracket-escape column names, build one '?'
    placeholder per column, pad a short row with None, and trim a long
    row - exercising the real method instead of re-implementing its
    logic (padding/trimming/placeholders/escaping) inline in the test.
    """
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_sqlserver_db.engine.raw_connection.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    csv_data = (
        "id\tuser name\tvalue\n"
        "1\tshort\n"  # fewer values than headers -> padded with None
        "2\tlong\textra\tvalues\n"  # more values than headers -> trimmed
    )
    with patch("builtins.open", mock_open(read_data=csv_data)):
        mock_sqlserver_db._bulk_load("person", Path("/data/person.csv"))

    insert_sql, short_row = mock_cursor.execute.call_args_list[0][0]
    assert insert_sql == (
        "INSERT INTO [cdm].[person] ([id], [user name], [value]) "
        "VALUES (?, ?, ?)"
    )
    assert short_row == ["1", "short", None]

    _, long_row = mock_cursor.execute.call_args_list[1][0]
    assert long_row == ["2", "long", "extra"]
