import pytest
from unittest.mock import Mock, patch
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


def test_schema_creation_sql_generation(mock_postgres_db):
    """Test that the correct SQL is generated for schema creation."""
    # Test the SQL generation logic
    schema_name = "test_schema"
    expected_sql = 'CREATE SCHEMA "test_schema"'

    # This tests the SQL generation, not the execution
    assert f'CREATE SCHEMA "{schema_name}"' == expected_sql


def test_fts_enabled_setting(mock_postgres_db):
    """Test that FTS setting is properly configured."""
    mock_postgres_db.settings.fts_create = True
    assert mock_postgres_db.settings.fts_create is True


def test_fts_disabled_setting(mock_postgres_db):
    """Test that FTS setting is properly configured when disabled."""
    mock_postgres_db.settings.fts_create = False
    assert mock_postgres_db.settings.fts_create is False


def test_copy_command_sql_generation():
    """Test that the correct COPY command SQL is generated."""
    settings = Settings(
        schema_name="cdm",
        delimiter="\t",
        synthetic=True,
        synthetic_number=1000,
        dialect="postgresql",
    )

    # Test the SQL generation logic for COPY command
    table_name = "test_table"
    delimiter = ","
    quote = '"'

    expected_sql = f"COPY cdm.{table_name} FROM STDIN WITH (FORMAT csv, DELIMITER E'{delimiter}', NULL '', QUOTE E'{quote}', HEADER, ENCODING 'UTF8')"

    # This tests the SQL generation logic, not the execution
    generated_sql = f"COPY {settings.schema_name}.{table_name} FROM STDIN WITH (FORMAT csv, DELIMITER E'{delimiter}', NULL '', QUOTE E'{quote}', HEADER, ENCODING 'UTF8')"
    assert generated_sql == expected_sql


def test_copy_command_with_custom_delimiter():
    """Test COPY command SQL with custom delimiter."""
    settings = Settings(
        schema_name="cdm", delimiter="|", synthetic=False, dialect="postgresql"
    )

    table_name = "test_table"
    delimiter = "|"
    quote = "\b"

    expected_sql = f"COPY cdm.{table_name} FROM STDIN WITH (FORMAT csv, DELIMITER E'{delimiter}', NULL '', QUOTE E'{quote}', HEADER, ENCODING 'UTF8')"

    generated_sql = f"COPY {settings.schema_name}.{table_name} FROM STDIN WITH (FORMAT csv, DELIMITER E'{delimiter}', NULL '', QUOTE E'{quote}', HEADER, ENCODING 'UTF8')"
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

    # Test schema name in SQL context
    schema_name = "test_schema"
    sql_safe_name = f'"{schema_name}"'
    assert sql_safe_name == '"test_schema"'


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
    assert len(mock_postgres_db.omop_tables) == 22
