import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from typing import Union

from omop_lite.settings import Settings
from omop_lite.db.base import Database


class TestDatabase(Database):
    """Concrete implementation of Database for testing."""

    def create_schema(self, schema_name: str) -> None:
        pass

    def _bulk_load(self, table_name: str, file_path: Union[Path, str]) -> None:
        pass


class TestDatabaseBase:
    """Test cases for the Database base class."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create test settings."""
        return Settings(
            db_host="localhost",
            db_port=5432,
            db_user="test_user",
            db_password="test_password",
            db_name="test_db",
            schema_name="test_schema",
            dialect="postgresql",
        )

    @pytest.fixture
    def database(self, settings: Settings) -> TestDatabase:
        """Create a test database instance."""
        return TestDatabase(settings)

    def test_init(self, database: TestDatabase, settings: Settings) -> None:
        """Test database initialization."""
        assert database.settings == settings
        assert database.engine is None
        assert database.metadata is None
        assert database.file_path is None
        assert len(database.omop_tables) == 22
        assert "PERSON" in database.omop_tables
        assert "CONCEPT" in database.omop_tables

    def test_dialect_property(self, database: TestDatabase) -> None:
        """Test dialect property returns correct value."""
        assert database.dialect == "postgresql"

    def test_file_exists_with_path(self, database: TestDatabase) -> None:
        """Test _file_exists with Path object."""
        with patch("pathlib.Path.is_file") as mock_is_file:
            mock_is_file.return_value = True
            file_path = Path("/test/file.csv")
            assert database._file_exists(file_path) is True

    def test_refresh_metadata_without_engine(self, database: TestDatabase) -> None:
        """Test refresh_metadata raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database not properly initialized"):
            database.refresh_metadata()

    def test_refresh_metadata_without_metadata(self, database: TestDatabase) -> None:
        """Test refresh_metadata raises error when metadata is None."""
        database.engine = Mock()
        with pytest.raises(RuntimeError, match="Database not properly initialized"):
            database.refresh_metadata()

    def test_refresh_metadata_success(self, database: TestDatabase) -> None:
        """Test refresh_metadata works with proper initialization."""
        database.engine = Mock()
        database.metadata = Mock()
        database.refresh_metadata()
        database.metadata.reflect.assert_called_once_with(bind=database.engine)

    def test_schema_exists_without_engine(self, database: TestDatabase) -> None:
        """Test schema_exists raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            database.schema_exists("test_schema")

    @patch("omop_lite.db.base.Database._execute_sql_file")
    def test_add_primary_keys(self, mock_execute_sql: Mock, database: TestDatabase) -> None:
        """Test add_primary_keys method."""
        database.file_path = Mock()
        database.file_path.joinpath.return_value = "primary_keys.sql"

        database.add_primary_keys()

        mock_execute_sql.assert_called_once_with("primary_keys.sql")

    @patch("omop_lite.db.base.Database._execute_sql_file")
    def test_add_constraints(self, mock_execute_sql: Mock, database: TestDatabase) -> None:
        """Test add_constraints method."""
        database.file_path = Mock()
        database.file_path.joinpath.return_value = "constraints.sql"

        database.add_constraints()

        mock_execute_sql.assert_called_once_with("constraints.sql")

    @patch("omop_lite.db.base.Database._execute_sql_file")
    def test_add_indices(self, mock_execute_sql: Mock, database: TestDatabase) -> None:
        """Test add_indices method."""
        database.file_path = Mock()
        database.file_path.joinpath.return_value = "indices.sql"

        database.add_indices()

        mock_execute_sql.assert_called_once_with("indices.sql")

    @patch("omop_lite.db.base.Database.add_primary_keys")
    @patch("omop_lite.db.base.Database.add_constraints")
    @patch("omop_lite.db.base.Database.add_indices")
    def test_add_all_constraints(
        self, mock_indices: Mock, mock_constraints: Mock, mock_primary_keys: Mock, database: TestDatabase
    ) -> None:
        """Test add_all_constraints method calls all constraint methods."""
        database.add_all_constraints()

        mock_primary_keys.assert_called_once()
        mock_constraints.assert_called_once()
        mock_indices.assert_called_once()

    def test_drop_tables_without_engine(self, database: TestDatabase) -> None:
        """Test drop_tables raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database not properly initialized"):
            database.drop_tables()

    def test_drop_tables_without_metadata(self, database: TestDatabase) -> None:
        """Test drop_tables raises error when metadata is None."""
        database.engine = Mock()
        with pytest.raises(RuntimeError, match="Database not properly initialized"):
            database.drop_tables()

    def test_drop_tables_success(self, database: TestDatabase) -> None:
        """Test drop_tables works with proper initialization."""
        database.engine = Mock()
        database.metadata = Mock()

        database.drop_tables()

        database.metadata.drop_all.assert_called_once_with(bind=database.engine)

    def test_drop_schema_without_engine(self, database: TestDatabase) -> None:
        """Test drop_schema raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            database.drop_schema("test_schema")

    @patch("omop_lite.db.base.Database.drop_tables")
    @patch("omop_lite.db.base.Database.drop_schema")
    def test_drop_all(self, mock_drop_schema: Mock, mock_drop_tables: Mock, database: TestDatabase) -> None:
        """Test drop_all method."""
        database.drop_all("test_schema")

        mock_drop_tables.assert_called_once()
        mock_drop_schema.assert_called_once_with("test_schema")

    @patch("omop_lite.db.base.Database.drop_tables")
    @patch("omop_lite.db.base.Database.drop_schema")
    def test_drop_all_public_schema(self, mock_drop_schema: Mock, mock_drop_tables: Mock, database: TestDatabase) -> None:
        """Test drop_all method with public schema (should not drop schema)."""
        database.drop_all("public")

        mock_drop_tables.assert_called_once()
        mock_drop_schema.assert_not_called()

    @patch("pathlib.Path.exists")
    def test_get_data_dir_real_data(self, mock_exists: Mock, database: TestDatabase) -> None:
        """Test _get_data_dir with real data directory."""
        database.settings.synthetic = False
        database.settings.data_dir = "/test/data"
        mock_exists.return_value = True

        result = database._get_data_dir()

        assert str(result) == "/test/data"

    @patch("pathlib.Path.exists")
    def test_get_data_dir_real_data_not_exists(self, mock_exists: Mock, database: TestDatabase) -> None:
        """Test _get_data_dir raises error when data directory doesn't exist."""
        database.settings.synthetic = False
        database.settings.data_dir = "/nonexistent/data"
        mock_exists.return_value = False

        with pytest.raises(
            FileNotFoundError, match="Data directory /nonexistent/data does not exist"
        ):
            database._get_data_dir()

    def test_get_delimiter_synthetic_1000(self, database: TestDatabase) -> None:
        """Test _get_delimiter with synthetic 1000 data."""
        database.settings.synthetic = True
        database.settings.synthetic_number = 1000

        result = database._get_delimiter()

        assert result == ","

    def test_get_delimiter_synthetic_100(self, database: TestDatabase) -> None:
        """Test _get_delimiter with synthetic 100 data."""
        database.settings.synthetic = True
        database.settings.synthetic_number = 100
        database.settings.delimiter = "\t"

        result = database._get_delimiter()

        assert result == "\t"

    def test_get_delimiter_real_data(self, database: TestDatabase) -> None:
        """Test _get_delimiter with real data."""
        database.settings.synthetic = False
        database.settings.delimiter = "|"

        result = database._get_delimiter()

        assert result == "|"

    def test_get_quote_synthetic_1000(self, database: TestDatabase) -> None:
        """Test _get_quote with synthetic 1000 data."""
        database.settings.synthetic = True
        database.settings.synthetic_number = 1000

        result = database._get_quote()

        assert result == '"'

    def test_get_quote_synthetic_100(self, database: TestDatabase) -> None:
        """Test _get_quote with synthetic 100 data."""
        database.settings.synthetic = True
        database.settings.synthetic_number = 100

        result = database._get_quote()

        assert result == "\b"

    def test_get_quote_real_data(self, database: TestDatabase) -> None:
        """Test _get_quote with real data."""
        database.settings.synthetic = False

        result = database._get_quote()

        assert result == "\b"

    @patch("builtins.open")
    @patch("sqlalchemy.sql.text")
    def test_execute_sql_file_without_engine(self, mock_text: Mock, mock_open: Mock, database: TestDatabase) -> None:
        """Test _execute_sql_file raises error when engine is None."""
        mock_open.return_value.__enter__.return_value.read.return_value = "SELECT 1"

        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            database._execute_sql_file("test.sql")

    @patch("builtins.open")
    @patch("sqlalchemy.sql.text")
    def test_execute_sql_file_success(self, mock_text: Mock, mock_open: Mock, database: TestDatabase) -> None:
        """Test _execute_sql_file works with proper initialization."""
        database.engine = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()
        database.engine.raw_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        mock_open.return_value.__enter__.return_value.read.return_value = (
            "SELECT @cdmDatabaseSchema"
        )

        database._execute_sql_file("test.sql")

        mock_open.assert_called_with("test.sql", "r")
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()
