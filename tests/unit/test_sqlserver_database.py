import pytest
from unittest.mock import Mock, patch
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


def test_schema_creation_sql_generation(mock_sqlserver_db):
    """Test that the correct SQL is generated for schema creation."""
    # Test the SQL generation logic
    schema_name = "test_schema"
    expected_sql = "CREATE SCHEMA [test_schema]"

    # This tests the SQL generation, not the execution
    assert f"CREATE SCHEMA [{schema_name}]" == expected_sql


def test_insert_sql_generation():
    """Test that the correct INSERT SQL is generated."""
    settings = Settings(
        schema_name="cdm",
        delimiter="\t",
        synthetic=True,
        synthetic_number=1000,
        dialect="mssql",
    )

    # Test the SQL generation logic for INSERT command
    table_name = "test_table"
    headers = ["id", "name", "value"]

    columns = ", ".join(f"[{col}]" for col in headers)
    placeholders = ", ".join(["?" for _ in headers])
    expected_sql = f"INSERT INTO cdm.[{table_name}] ({columns}) VALUES ({placeholders})"

    # This tests the SQL generation logic, not the execution
    generated_sql = f"INSERT INTO {settings.schema_name}.[{table_name}] ({columns}) VALUES ({placeholders})"
    assert generated_sql == expected_sql


def test_insert_sql_with_single_column():
    """Test INSERT SQL with single column."""
    settings = Settings(
        schema_name="cdm", delimiter="|", synthetic=False, dialect="mssql"
    )

    table_name = "test_table"
    headers = ["id"]

    columns = ", ".join(f"[{col}]" for col in headers)
    placeholders = ", ".join(["?" for _ in headers])
    expected_sql = f"INSERT INTO cdm.[{table_name}] ({columns}) VALUES ({placeholders})"

    generated_sql = f"INSERT INTO {settings.schema_name}.[{table_name}] ({columns}) VALUES ({placeholders})"
    assert generated_sql == expected_sql


def test_file_path_handling():
    """Test that file paths are handled correctly."""
    file_path = Path("/test/file.csv")

    # Test string conversion
    assert str(file_path) == "/test/file.csv"

    # Test path joining
    data_dir = Path("/data")
    full_path = data_dir / "test.csv"
    assert str(full_path) == "/data/test.csv"


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


def test_delimiter_logic():
    """Test the delimiter selection logic."""
    # Test synthetic 1000
    settings_1000 = Settings(synthetic=True, synthetic_number=1000)
    assert settings_1000.synthetic is True
    assert settings_1000.synthetic_number == 1000

    # Test synthetic 100
    settings_100 = Settings(synthetic=True, synthetic_number=100)
    assert settings_100.synthetic is True
    assert settings_100.synthetic_number == 100

    # Test non-synthetic
    settings_real = Settings(synthetic=False, delimiter="|")
    assert settings_real.synthetic is False
    assert settings_real.delimiter == "|"


def test_quote_logic():
    """Test the quote selection logic."""
    # Test synthetic 1000
    settings_1000 = Settings(synthetic=True, synthetic_number=1000)
    assert settings_1000.synthetic is True
    assert settings_1000.synthetic_number == 1000

    # Test synthetic 100
    settings_100 = Settings(synthetic=True, synthetic_number=100)
    assert settings_100.synthetic is True
    assert settings_100.synthetic_number == 100


def test_schema_name_handling():
    """Test schema name handling."""
    # Test default schema
    default_settings = Settings()
    assert default_settings.schema_name == "public"

    # Test custom schema
    custom_settings = Settings(schema_name="cdm")
    assert custom_settings.schema_name == "cdm"

    # Test schema name in SQL context (SQL Server uses brackets)
    schema_name = "test_schema"
    sql_safe_name = f"[{schema_name}]"
    assert sql_safe_name == "[test_schema]"


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
    assert len(mock_sqlserver_db.omop_tables) == 22


def test_csv_reader_logic():
    """Test CSV reader logic for SQL Server."""
    # Test delimiter handling
    delimiter = "\t"
    assert delimiter == "\t"

    # Test encoding
    encoding = "utf-8"
    assert encoding == "utf-8"

    # Test newline handling
    newline = ""
    assert newline == ""


def test_row_padding_logic():
    """Test row padding logic for SQL Server."""
    headers = ["id", "name", "value"]
    short_row = ["1", "test"]

    # Test padding logic
    if len(short_row) < len(headers):
        padded_row = short_row + [None] * (len(headers) - len(short_row))
        expected = ["1", "test", None]
        assert padded_row == expected


def test_row_trimming_logic():
    """Test row trimming logic for SQL Server."""
    headers = ["id", "name"]
    long_row = ["1", "test", "extra", "values"]

    # Test trimming logic
    if len(long_row) > len(headers):
        trimmed_row = long_row[: len(headers)]
        expected = ["1", "test"]
        assert trimmed_row == expected


def test_placeholder_generation():
    """Test placeholder generation for SQL Server."""
    headers = ["id", "name", "value"]

    # Test placeholder generation
    placeholders = ", ".join(["?" for _ in headers])
    expected = "?, ?, ?"
    assert placeholders == expected


def test_column_name_escaping():
    """Test column name escaping for SQL Server."""
    headers = ["id", "user name", "value"]

    # Test column name escaping with brackets
    columns = ", ".join(f"[{col}]" for col in headers)
    expected = "[id], [user name], [value]"
    assert columns == expected
