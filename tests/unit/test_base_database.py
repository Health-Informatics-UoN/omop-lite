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

    # Tests for _file_exists method
    def test_file_exists_with_traversable(self, database: TestDatabase) -> None:
        """Test _file_exists with Traversable object."""
        mock_traversable = Mock()
        mock_traversable.is_file.return_value = True
        
        result = database._file_exists(mock_traversable)
        
        assert result is True
        mock_traversable.is_file.assert_called_once()

    def test_file_exists_with_path(self, database: TestDatabase) -> None:
        """Test _file_exists with Path object."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        
        result = database._file_exists(mock_path)
        
        assert result is True
        mock_path.exists.assert_called_once()

    # Tests for _wait_for_file method
    @patch("omop_lite.db.base.time.time")
    @patch("omop_lite.db.base.time.sleep")
    def test_wait_for_file_synthetic_true_immediate_check(self, mock_sleep: Mock, mock_time: Mock, database: TestDatabase) -> None:
        """Test _wait_for_file with synthetic=True should just check file existence."""
        database.settings.synthetic = True
        mock_file_path = Mock()
        
        # Mock _file_exists to return True
        with patch.object(database, '_file_exists', return_value=True):
            result = database._wait_for_file(mock_file_path)
        
        assert result is True
        mock_sleep.assert_not_called()  # Should not sleep when synthetic=True

    @patch("omop_lite.db.base.time.time")
    @patch("omop_lite.db.base.time.sleep")
    def test_wait_for_file_synthetic_true_file_not_exists(self, mock_sleep: Mock, mock_time: Mock, database: TestDatabase) -> None:
        """Test _wait_for_file with synthetic=True when file doesn't exist."""
        database.settings.synthetic = True
        mock_file_path = Mock()
        
        # Mock _file_exists to return False
        with patch.object(database, '_file_exists', return_value=False):
            result = database._wait_for_file(mock_file_path)
        
        assert result is False
        mock_sleep.assert_not_called()  # Should not sleep when synthetic=True

    @patch("omop_lite.db.base.time.time")
    @patch("omop_lite.db.base.time.sleep")
    def test_wait_for_file_synthetic_false_file_exists_immediately(self, mock_sleep: Mock, mock_time: Mock, database: TestDatabase) -> None:
        """Test _wait_for_file with synthetic=False when file exists immediately."""
        database.settings.synthetic = False
        mock_file_path = Mock()
        
        # Mock time to return consistent values
        mock_time.return_value = 100.0
        
        # Mock _file_exists to return True immediately
        with patch.object(database, '_file_exists', return_value=True):
            result = database._wait_for_file(mock_file_path)
        
        assert result is True
        mock_sleep.assert_not_called()  # Should not sleep if file exists immediately

    @patch("omop_lite.db.base.time.time")
    @patch("omop_lite.db.base.time.sleep")
    def test_wait_for_file_synthetic_false_file_appears_after_wait(self, mock_sleep: Mock, mock_time: Mock, database: TestDatabase) -> None:
        """Test _wait_for_file with synthetic=False when file appears after waiting."""
        database.settings.synthetic = False
        mock_file_path = Mock()
        
        # Mock time to simulate progression
        mock_time.side_effect = [100.0, 105.0, 110.0]  # 3 calls: start, after first sleep, after second sleep
        
        # Mock _file_exists to return False initially, then True
        with patch.object(database, '_file_exists', side_effect=[False, False, True]):
            result = database._wait_for_file(mock_file_path)
        
        assert result is True
        assert mock_sleep.call_count == 2  # Should sleep twice before file appears

    @patch("omop_lite.db.base.time.time")
    @patch("omop_lite.db.base.time.sleep")
    def test_wait_for_file_synthetic_false_timeout(self, mock_sleep: Mock, mock_time: Mock, database: TestDatabase) -> None:
        """Test _wait_for_file with synthetic=False when timeout is reached."""
        database.settings.synthetic = False
        mock_file_path = Mock()
        
        # Mock time to simulate timeout (300 seconds default)
        mock_time.side_effect = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0, 145.0, 150.0, 151.0]  # 12 calls to simulate timeout
        
        # Mock _file_exists to always return False
        with patch.object(database, '_file_exists', return_value=False):
            result = database._wait_for_file(mock_file_path, max_wait_time=50)  # Short timeout for testing
        
        assert result is False
        # Should sleep multiple times before timeout
        assert mock_sleep.call_count >= 10

    @patch("omop_lite.db.base.time.time")
    @patch("omop_lite.db.base.time.sleep")
    def test_wait_for_file_custom_timeout(self, mock_sleep: Mock, mock_time: Mock, database: TestDatabase) -> None:
        """Test _wait_for_file with custom timeout."""
        database.settings.synthetic = False
        mock_file_path = Mock()
        
        # Mock time to simulate short timeout
        mock_time.side_effect = [100.0, 105.0, 110.0]
        
        # Mock _file_exists to always return False
        with patch.object(database, '_file_exists', return_value=False):
            result = database._wait_for_file(mock_file_path, max_wait_time=5)  # Very short timeout
        
        assert result is False
        assert mock_sleep.call_count == 1  # Should sleep once before timeout

    # Tests for load_data method with waiting functionality
    @patch("omop_lite.db.base.Database._get_data_dir")
    @patch("omop_lite.db.base.Database._bulk_load")
    def test_load_data_with_waiting_synthetic_false(self, mock_bulk_load: Mock, mock_get_data_dir: Mock, database: TestDatabase) -> None:
        """Test load_data with synthetic=False uses waiting functionality."""
        database.settings.synthetic = False
        mock_data_dir = Mock()
        mock_get_data_dir.return_value = mock_data_dir
        mock_data_dir.__truediv__ = lambda self, other: f"{mock_data_dir}/{other}"
        
        # Mock _wait_for_file to return True for one table
        with patch.object(database, '_wait_for_file', return_value=True):
            database.load_data(["PERSON"])
        
        # Should call _wait_for_file for PERSON.csv
        mock_bulk_load.assert_called_once()

    @patch("omop_lite.db.base.Database._get_data_dir")
    @patch("omop_lite.db.base.Database._bulk_load")
    def test_load_data_with_waiting_synthetic_true(self, mock_bulk_load: Mock, mock_get_data_dir: Mock, database: TestDatabase) -> None:
        """Test load_data with synthetic=True uses immediate file checking."""
        database.settings.synthetic = True
        mock_data_dir = Mock()
        mock_get_data_dir.return_value = mock_data_dir
        mock_data_dir.__truediv__ = lambda self, other: f"{mock_data_dir}/{other}"
        
        # Mock _wait_for_file to return True for one table
        with patch.object(database, '_wait_for_file', return_value=True):
            database.load_data(["PERSON"])
        
        # Should call _wait_for_file for PERSON.csv
        mock_bulk_load.assert_called_once()

    @patch("omop_lite.db.base.Database._get_data_dir")
    @patch("omop_lite.db.base.Database._bulk_load")
    def test_load_data_file_not_found_after_waiting(self, mock_bulk_load: Mock, mock_get_data_dir: Mock, database: TestDatabase) -> None:
        """Test load_data when file is not found after waiting."""
        database.settings.synthetic = False
        mock_data_dir = Mock()
        mock_get_data_dir.return_value = mock_data_dir
        mock_data_dir.__truediv__ = lambda self, other: f"{mock_data_dir}/{other}"
        
        # Mock _wait_for_file to return False (file not found)
        with patch.object(database, '_wait_for_file', return_value=False):
            database.load_data(["PERSON"])
        
        # Should not call _bulk_load when file is not found
        mock_bulk_load.assert_not_called()

    @patch("omop_lite.db.base.Database._get_data_dir")
    @patch("omop_lite.db.base.Database._bulk_load")
    def test_load_data_multiple_tables_some_missing(self, mock_bulk_load: Mock, mock_get_data_dir: Mock, database: TestDatabase) -> None:
        """Test load_data with multiple tables, some files missing."""
        database.settings.synthetic = False
        mock_data_dir = Mock()
        mock_get_data_dir.return_value = mock_data_dir
        mock_data_dir.__truediv__ = lambda self, other: f"{mock_data_dir}/{other}"
        
        # Mock _wait_for_file to return True for PERSON, False for CONCEPT
        def mock_wait_for_file(file_path):
            if "PERSON.csv" in str(file_path):
                return True
            return False
        
        with patch.object(database, '_wait_for_file', side_effect=mock_wait_for_file):
            database.load_data(["PERSON", "CONCEPT"])
        
        # Should only call _bulk_load for PERSON (which was found)
        assert mock_bulk_load.call_count == 1
        # Check that the call was for PERSON table
        call_args = mock_bulk_load.call_args
        assert "person" in call_args[0][0]  # table_name should be "person"

    @patch("omop_lite.db.base.Database._get_data_dir")
    @patch("omop_lite.db.base.Database._bulk_load")
    def test_load_data_bulk_load_exception(self, mock_bulk_load: Mock, mock_get_data_dir: Mock, database: TestDatabase) -> None:
        """Test load_data handles exceptions from _bulk_load."""
        database.settings.synthetic = False
        mock_data_dir = Mock()
        mock_get_data_dir.return_value = mock_data_dir
        mock_data_dir.__truediv__ = lambda self, other: f"{mock_data_dir}/{other}"
        
        # Mock _wait_for_file to return True
        with patch.object(database, '_wait_for_file', return_value=True):
            # Mock _bulk_load to raise an exception
            mock_bulk_load.side_effect = Exception("Bulk load failed")
            
            # Should not raise exception, should continue processing
            database.load_data(["PERSON"])
        
        # Should still call _bulk_load even though it fails
        mock_bulk_load.assert_called_once()
