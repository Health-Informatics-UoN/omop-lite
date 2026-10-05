import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from typing import Union

from omop_lite.settings import Settings
from omop_lite.db.base import Database, SqlBatchResult, _split_sql_statements


class TestDatabase(Database):
    """Concrete implementation of Database for testing."""

    def create_schema(self, schema_name: str) -> None:
        pass

    def _bulk_load(self, table_name: str, file_path: Union[Path, str]) -> None:
        pass


class TestDatabaseBase:
    """Test cases for the Database base class."""

    @pytest.fixture
    def settings(self):
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
    def database(self, settings):
        """Create a test database instance."""
        return TestDatabase(settings)

    def test_init(self, database, settings):
        """Test database initialization."""
        assert database.settings == settings
        assert database.engine is None
        assert database.metadata is None
        assert database.file_path is None
        assert len(database.omop_tables) == 39
        assert "PERSON" in database.omop_tables
        assert "CONCEPT" in database.omop_tables

    def test_dialect_property(self, database):
        """Test dialect property returns correct value."""
        assert database.dialect == "postgresql"

    def test_file_exists_with_path(self, database):
        """Test _file_exists with Path object."""
        with patch("pathlib.Path.is_file") as mock_is_file:
            mock_is_file.return_value = True
            file_path = Path("/test/file.csv")
            assert database._file_exists(file_path) is True

    def test_refresh_metadata_without_engine(self, database):
        """Test refresh_metadata raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database not properly initialized"):
            database.refresh_metadata()

    def test_refresh_metadata_without_metadata(self, database):
        """Test refresh_metadata raises error when metadata is None."""
        database.engine = Mock()
        with pytest.raises(RuntimeError, match="Database not properly initialized"):
            database.refresh_metadata()

    def test_refresh_metadata_success(self, database):
        """Test refresh_metadata works with proper initialization."""
        database.engine = Mock()
        database.metadata = Mock()
        database.refresh_metadata()
        database.metadata.reflect.assert_called_once_with(
            bind=database.engine, extend_existing=True
        )

    def test_schema_exists_without_engine(self, database):
        """Test schema_exists raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            database.schema_exists("test_schema")

    def test_tables_exist_without_engine(self, database):
        """Test tables_exist raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            database.tables_exist("test_schema")

    def test_tables_exist_true(self, database):
        """tables_exist is True if any OMOP table is present, regardless of case."""
        database.engine = Mock()
        with patch("omop_lite.db.base.inspect") as mock_inspect:
            mock_inspect.return_value.get_table_names.return_value = [
                "some_other_table",
                "PERSON".lower(),
            ]
            assert database.tables_exist("test_schema") is True

    def test_tables_exist_false(self, database):
        """tables_exist is False when none of the OMOP tables are present."""
        database.engine = Mock()
        with patch("omop_lite.db.base.inspect") as mock_inspect:
            mock_inspect.return_value.get_table_names.return_value = ["unrelated"]
            assert database.tables_exist("test_schema") is False

    @patch("omop_lite.db.base.Database._apply_sql_statements")
    def test_add_primary_keys(self, mock_apply, database):
        """Test add_primary_keys method."""
        database.file_path = Mock()
        database.file_path.joinpath.return_value = "primary_keys.sql"
        mock_apply.return_value = SqlBatchResult(succeeded=39, failed=0)

        result = database.add_primary_keys()

        mock_apply.assert_called_once_with("primary_keys.sql")
        assert result == SqlBatchResult(succeeded=39, failed=0)

    @patch("omop_lite.db.base.Database.refresh_metadata")
    @patch("omop_lite.db.base.Database._apply_sql_statements")
    def test_add_constraints(self, mock_apply, mock_refresh_metadata, database):
        """add_constraints must refresh metadata afterwards, so drop_tables
        later knows about any foreign keys constraints.sql just added (see
        #145's CI fallout: stale metadata gave drop_tables the wrong order).
        It must also return the batch result as-is, not swallow it."""
        database.file_path = Mock()
        database.file_path.joinpath.return_value = "constraints.sql"
        mock_apply.return_value = SqlBatchResult(succeeded=170, failed=6)

        result = database.add_constraints()

        mock_apply.assert_called_once_with("constraints.sql")
        mock_refresh_metadata.assert_called_once()
        assert result == SqlBatchResult(succeeded=170, failed=6)

    @patch("omop_lite.db.base.Database._apply_sql_statements")
    def test_add_indices(self, mock_apply, database):
        """Test add_indices method."""
        database.file_path = Mock()
        database.file_path.joinpath.return_value = "indices.sql"
        mock_apply.return_value = SqlBatchResult(succeeded=100, failed=2)

        result = database.add_indices()

        mock_apply.assert_called_once_with("indices.sql")
        assert result == SqlBatchResult(succeeded=100, failed=2)

    @patch("omop_lite.db.base.Database.add_primary_keys")
    @patch("omop_lite.db.base.Database.add_constraints")
    @patch("omop_lite.db.base.Database.add_indices")
    def test_add_all_constraints(
        self, mock_indices, mock_constraints, mock_primary_keys, database
    ):
        """add_all_constraints must call all three constraint methods and
        sum their results, not just call them for effect."""
        mock_primary_keys.return_value = SqlBatchResult(succeeded=39, failed=0)
        mock_constraints.return_value = SqlBatchResult(succeeded=170, failed=6)
        mock_indices.return_value = SqlBatchResult(succeeded=100, failed=2)

        result = database.add_all_constraints()

        mock_primary_keys.assert_called_once()
        mock_constraints.assert_called_once()
        mock_indices.assert_called_once()
        assert result == SqlBatchResult(succeeded=309, failed=8)

    def test_drop_tables_without_engine(self, database):
        """Test drop_tables raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database not properly initialized"):
            database.drop_tables()

    def test_drop_tables_without_metadata(self, database):
        """Test drop_tables raises error when metadata is None."""
        database.engine = Mock()
        with pytest.raises(RuntimeError, match="Database not properly initialized"):
            database.drop_tables()

    def test_drop_tables_success(self, database):
        """Test drop_tables works with proper initialization."""
        database.engine = Mock()
        database.metadata = Mock()

        database.drop_tables()

        database.metadata.drop_all.assert_called_once_with(bind=database.engine)

    def test_drop_schema_without_engine(self, database):
        """Test drop_schema raises error when engine is None."""
        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            database.drop_schema("test_schema")

    @patch("omop_lite.db.base.Database.drop_tables")
    @patch("omop_lite.db.base.Database.drop_schema")
    def test_drop_all(self, mock_drop_schema, mock_drop_tables, database):
        """Test drop_all method."""
        database.drop_all("test_schema")

        mock_drop_tables.assert_called_once()
        mock_drop_schema.assert_called_once_with("test_schema")

    @patch("omop_lite.db.base.Database.drop_tables")
    @patch("omop_lite.db.base.Database.drop_schema")
    def test_drop_all_public_schema(self, mock_drop_schema, mock_drop_tables, database):
        """Test drop_all method with public schema (should not drop schema)."""
        database.drop_all("public")

        mock_drop_tables.assert_called_once()
        mock_drop_schema.assert_not_called()

    @patch("pathlib.Path.exists")
    def test_get_data_dir_real_data(self, mock_exists, database):
        """Test _get_data_dir with real data directory."""
        database.settings.synthetic = False
        database.settings.data_dir = "/test/data"
        mock_exists.return_value = True

        result = database._get_data_dir()

        assert str(result) == "/test/data"

    @patch("pathlib.Path.exists")
    def test_get_data_dir_real_data_not_exists(self, mock_exists, database):
        """Test _get_data_dir raises error when data directory doesn't exist."""
        database.settings.synthetic = False
        database.settings.data_dir = "/nonexistent/data"
        mock_exists.return_value = False

        with pytest.raises(
            FileNotFoundError, match="Data directory /nonexistent/data does not exist"
        ):
            database._get_data_dir()

    def test_get_delimiter_synthetic_1000(self, database):
        """Test _get_delimiter with synthetic 1000 data."""
        database.settings.synthetic = True
        database.settings.synthetic_number = 1000

        result = database._get_delimiter()

        assert result == ","

    def test_get_delimiter_synthetic_100(self, database):
        """Test _get_delimiter with synthetic 100 data."""
        database.settings.synthetic = True
        database.settings.synthetic_number = 100
        database.settings.delimiter = "\t"

        result = database._get_delimiter()

        assert result == "\t"

    def test_get_delimiter_real_data(self, database):
        """Test _get_delimiter with real data."""
        database.settings.synthetic = False
        database.settings.delimiter = "|"

        result = database._get_delimiter()

        assert result == "|"

    def test_get_quote_synthetic_1000(self, database):
        """Test _get_quote with synthetic 1000 data."""
        database.settings.synthetic = True
        database.settings.synthetic_number = 1000

        result = database._get_quote()

        assert result == '"'

    def test_get_quote_synthetic_100(self, database):
        """Test _get_quote with synthetic 100 data."""
        database.settings.synthetic = True
        database.settings.synthetic_number = 100

        result = database._get_quote()

        assert result == "\b"

    def test_get_quote_real_data(self, database):
        """Test _get_quote with real data."""
        database.settings.synthetic = False

        result = database._get_quote()

        assert result == "\b"

    def test_load_data_continues_after_table_failure(self, database):
        """A failing table must not stop the rest of load_data's loop.

        Real OMOP CSVs (vocabulary files especially) sometimes contain rows
        that fail to load. Postgres/DuckDB's COPY fails the whole table on
        one bad row, so load_data catches per-table and keeps going - this
        locks in that intentional behaviour.
        """
        database._get_data_dir = Mock(return_value=Path("/data"))
        database._file_exists = Mock(return_value=True)

        attempted = []

        def fake_bulk_load(table_name, file_path):
            attempted.append(table_name)
            if table_name == database.omop_tables[0].lower():
                raise RuntimeError("bad row")

        database._bulk_load = Mock(side_effect=fake_bulk_load)

        database.load_data()  # must not raise

        assert attempted == [t.lower() for t in database.omop_tables]

    def test_quote_identifier_postgresql(self, database):
        """Postgres/duckdb identifiers are double-quoted, preserving case."""
        database.settings.dialect = "postgresql"
        assert database._quote_identifier("MixedCase") == '"MixedCase"'

    def test_quote_identifier_duckdb(self, database):
        database.settings.dialect = "duckdb"
        assert database._quote_identifier("MixedCase") == '"MixedCase"'

    def test_quote_identifier_mssql(self, database):
        """SQL Server identifiers are bracket-quoted."""
        database.settings.dialect = "mssql"
        assert database._quote_identifier("MixedCase") == "[MixedCase]"

    @patch("builtins.open")
    @patch("sqlalchemy.sql.text")
    def test_execute_sql_file_quotes_schema_placeholder(
        self, mock_text, mock_open, database
    ):
        """@cdmDatabaseSchema must substitute to a quoted identifier.

        Mixed-case schema names are folded to lower-case by postgres/duckdb
        when left unquoted, silently diverging from the exact-case schema
        create_schema (which already quotes) created - see #97.
        """
        database.engine = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()
        database.engine.raw_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        database.settings.schema_name = "MixedCase"

        mock_open.return_value.__enter__.return_value.read.return_value = (
            "SELECT * FROM @cdmDatabaseSchema.person"
        )

        database._execute_sql_file("test.sql")

        executed_sql = mock_cursor.execute.call_args[0][0]
        assert executed_sql == 'SELECT * FROM "MixedCase".person'

    @patch("builtins.open")
    @patch("sqlalchemy.sql.text")
    def test_execute_sql_file_without_engine(self, mock_text, mock_open, database):
        """Test _execute_sql_file raises error when engine is None."""
        mock_open.return_value.__enter__.return_value.read.return_value = "SELECT 1"

        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            database._execute_sql_file("test.sql")

    @patch("builtins.open")
    @patch("sqlalchemy.sql.text")
    def test_execute_sql_file_success(self, mock_text, mock_open, database):
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

    @patch("builtins.open")
    @patch("sqlalchemy.sql.text")
    def test_execute_sql_file_failure_reraises(self, mock_text, mock_open, database):
        """Test _execute_sql_file re-raises on failure instead of swallowing it."""
        database.engine = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()
        database.engine.raw_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = RuntimeError("boom")

        mock_open.return_value.__enter__.return_value.read.return_value = (
            "SELECT @cdmDatabaseSchema"
        )

        with pytest.raises(RuntimeError, match="boom"):
            database._execute_sql_file("test.sql")

        mock_connection.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch("builtins.open")
    @patch("sqlalchemy.sql.text")
    def test_execute_sql_file_failure_rollback_also_fails(
        self, mock_text, mock_open, database
    ):
        """Test the original error still propagates when rollback itself fails."""
        database.engine = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()
        database.engine.raw_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = RuntimeError("boom")
        mock_connection.rollback.side_effect = Exception("no active transaction")

        mock_open.return_value.__enter__.return_value.read.return_value = (
            "SELECT @cdmDatabaseSchema"
        )

        with pytest.raises(RuntimeError, match="boom"):
            database._execute_sql_file("test.sql")

        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()

    def test_split_sql_statements_strips_comments(self):
        """Line (--) and block (/* */) comments must be removed, and only
        non-empty statements kept."""
        sql = """
        -- a leading comment
        /* a block
           comment */
        CREATE TABLE a (id int);
        -- between statements
        ALTER TABLE a ADD CONSTRAINT x PRIMARY KEY (id);
        """
        assert _split_sql_statements(sql) == [
            "CREATE TABLE a (id int)",
            "ALTER TABLE a ADD CONSTRAINT x PRIMARY KEY (id)",
        ]

    def test_split_sql_statements_empty(self):
        assert _split_sql_statements("-- just a comment\n") == []

    @patch("builtins.open")
    def test_apply_sql_statements_continues_past_failure(self, mock_open, database):
        """One failing statement must not block the others - this is the
        fix for real OMOP vocabulary gaps (see #145 follow-up): a single
        missing concept used to take down every other constraint too."""
        database.engine = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()
        database.engine.raw_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = [None, RuntimeError("fk violation"), None]

        mock_open.return_value.__enter__.return_value.read.return_value = (
            "STATEMENT ONE; STATEMENT TWO; STATEMENT THREE;"
        )

        result = database._apply_sql_statements("test.sql")

        assert result == SqlBatchResult(succeeded=2, failed=1)
        assert mock_cursor.execute.call_count == 3
        # The failed statement's rollback must not stop the next one running.
        assert mock_connection.commit.call_count == 2
        assert mock_connection.rollback.call_count == 1

    @patch("builtins.open")
    def test_apply_sql_statements_without_engine(self, mock_open, database):
        mock_open.return_value.__enter__.return_value.read.return_value = "SELECT 1;"
        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            database._apply_sql_statements("test.sql")
