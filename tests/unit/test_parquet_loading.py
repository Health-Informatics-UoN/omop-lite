import io
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from omop_lite.settings import Settings
from omop_lite.db.base import DataFormat


@pytest.fixture
def postgres_settings():
    return Settings(
        schema_name="cdm",
        dialect="postgresql",
    )


@pytest.fixture
def sqlserver_settings():
    return Settings(
        schema_name="cdm",
        dialect="mssql",
        parquet_batch_size=2,
    )


@pytest.fixture
def mock_postgres_db(postgres_settings):
    with (
        patch("omop_lite.db.postgres.create_engine") as mock_engine,
        patch("omop_lite.db.postgres.files"),
        patch("omop_lite.db.postgres.MetaData"),
    ):
        mock_engine.return_value = Mock()
        from omop_lite.db.postgres import PostgresDatabase

        db = PostgresDatabase(postgres_settings)
        return db


@pytest.fixture
def mock_sqlserver_db(sqlserver_settings):
    with (
        patch("omop_lite.db.sqlserver.create_engine") as mock_engine,
        patch("omop_lite.db.sqlserver.files"),
        patch("omop_lite.db.sqlserver.MetaData"),
    ):
        mock_engine.return_value = Mock()
        from omop_lite.db.sqlserver import SQLServerDatabase

        db = SQLServerDatabase(sqlserver_settings)
        return db


@pytest.fixture
def sample_parquet_file(tmp_path: Path) -> Path:
    """Write a small parquet file and return its path."""
    table = pa.table(
        {
            "person_id": [1, 2, 3],
            "year_of_birth": [1980, 1990, 2000],
            "gender_concept_id": [8507, 8532, 8507],
        }
    )
    parquet_path = tmp_path / "PERSON.parquet"
    pq.write_table(table, parquet_path)
    return parquet_path


class TestPostgresParquetLoading:
    @pytest.mark.unit
    def test_bulk_load_parquet_uses_copy(self, mock_postgres_db, sample_parquet_file):
        """Parquet loading pipes CSV bytes through copy_expert."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_postgres_db.engine.raw_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_postgres_db._bulk_load("person", sample_parquet_file, DataFormat.PARQUET)

        mock_cursor.copy_expert.assert_called_once()
        sql_arg = mock_cursor.copy_expert.call_args[0][0]
        assert "cdm.person" in sql_arg
        assert "FORMAT csv" in sql_arg
        assert "HEADER" in sql_arg

        buf_arg = mock_cursor.copy_expert.call_args[0][1]
        assert isinstance(buf_arg, io.BytesIO)
        content = buf_arg.read()
        assert b"person_id" in content
        assert b"1980" in content

        mock_conn.commit.assert_called_once()

    @pytest.mark.unit
    def test_bulk_load_csv_unchanged(self, mock_postgres_db, tmp_path: Path):
        """CSV loading still uses delimiter/quote from settings."""
        csv_file = tmp_path / "person.csv"
        csv_file.write_text("person_id\tyear_of_birth\n1\t1980\n")

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_postgres_db.engine.raw_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_postgres_db._bulk_load("person", csv_file, DataFormat.CSV)

        mock_cursor.copy_expert.assert_called_once()
        sql_arg = mock_cursor.copy_expert.call_args[0][0]
        assert "DELIMITER" in sql_arg
        mock_conn.commit.assert_called_once()


class TestSQLServerParquetLoading:
    @pytest.mark.unit
    def test_bulk_load_parquet_uses_executemany(
        self, mock_sqlserver_db, sample_parquet_file
    ):
        """Parquet loading calls executemany with batched rows."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_sqlserver_db.engine.raw_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # batch_size=2 with 3 rows → 2 batches
        mock_sqlserver_db._bulk_load("person", sample_parquet_file, DataFormat.PARQUET)

        assert mock_cursor.executemany.call_count == 2
        first_call_sql = mock_cursor.executemany.call_args_list[0][0][0]
        assert "cdm.[person]" in first_call_sql
        assert "[person_id]" in first_call_sql

        first_batch = mock_cursor.executemany.call_args_list[0][0][1]
        assert len(first_batch) == 2
        second_batch = mock_cursor.executemany.call_args_list[1][0][1]
        assert len(second_batch) == 1

        mock_conn.commit.assert_called_once()

    @pytest.mark.unit
    def test_bulk_load_parquet_row_values(
        self, mock_sqlserver_db, sample_parquet_file
    ):
        """Parquet rows are converted to Python native types."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_sqlserver_db.engine.raw_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_sqlserver_db.settings.parquet_batch_size = 100
        mock_sqlserver_db._bulk_load("person", sample_parquet_file, DataFormat.PARQUET)

        all_rows = mock_cursor.executemany.call_args[0][1]
        assert len(all_rows) == 3
        # Values should be native Python ints, not pyarrow scalars
        assert all_rows[0][0] == 1
        assert all_rows[1][1] == 1990
