import csv
from sqlalchemy import create_engine, MetaData, text
from importlib.resources import files
import logging
import pyarrow.parquet as pq
from .base import Database, DataFormat
from omop_lite.settings import Settings
from typing import Union
from pathlib import Path
from importlib.abc import Traversable

logger = logging.getLogger(__name__)


class SQLServerDatabase(Database):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.db_url = f"mssql+pyodbc://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
        self.engine = create_engine(self.db_url)
        self.metadata = MetaData(schema=settings.schema_name)
        self.metadata.reflect(bind=self.engine)
        self.file_path = files("omop_lite.scripts.mssql")

    def create_schema(self, schema_name: str) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        with self.engine.connect() as connection:
            sql = f"""
            IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema_name}')
            BEGIN
                EXEC('CREATE SCHEMA [{schema_name}]')
            END
            """
            connection.execute(text(sql))
            logger.info(f"Schema '{schema_name}' created.")
            connection.commit()

    def _bulk_load(
        self, table_name: str, file_path: Union[Path, Traversable], fmt: DataFormat
    ) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        if self.settings.skip_bad_rows:
            self._row_load(table_name, file_path, fmt)
            return

        conn = self.engine.raw_connection()
        try:
            cursor = conn.cursor()
            try:
                if fmt == DataFormat.PARQUET:
                    pa_table = pq.read_table(str(file_path))
                    col_names = pa_table.schema.names
                    columns = ", ".join(f"[{col}]" for col in col_names)
                    placeholders = ", ".join(["?" for _ in col_names])
                    insert_sql = f"INSERT INTO {self.settings.schema_name}.[{table_name}] ({columns}) VALUES ({placeholders})"
                    batch_size = self.settings.parquet_batch_size
                    rows = pa_table.to_pylist()
                    for i in range(0, len(rows), batch_size):
                        batch = [
                            [row[col] for col in col_names]
                            for row in rows[i : i + batch_size]
                        ]
                        cursor.executemany(insert_sql, batch)
                else:
                    delimiter = self._get_delimiter()
                    with open(str(file_path), "r", encoding="utf-8", newline="") as f:
                        reader = csv.reader(f, delimiter=delimiter)
                        headers = next(reader)
                        columns = ", ".join(f"[{col}]" for col in headers)
                        placeholders = ", ".join(["?" for _ in headers])
                        insert_sql = f"INSERT INTO {self.settings.schema_name}.[{table_name}] ({columns}) VALUES ({placeholders})"
                        for line_no, row in enumerate(reader, start=2):
                            if len(row) < len(headers):
                                row += [None] * (len(headers) - len(row))
                            elif len(row) > len(headers):
                                row = row[: len(headers)]
                            cursor.execute(insert_sql, row)
                conn.commit()
            finally:
                cursor.close()
        finally:
            conn.close()

    def _row_load(
        self, table_name: str, file_path: Union[Path, Traversable], fmt: DataFormat
    ) -> None:
        """Row-by-row fallback that skips invalid rows using savepoints."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        loaded = 0
        skipped = 0
        conn = self.engine.raw_connection()
        try:
            cursor = conn.cursor()
            try:
                if fmt == DataFormat.PARQUET:
                    pa_table = pq.read_table(str(file_path))
                    col_names = pa_table.schema.names
                    columns = ", ".join(f"[{col}]" for col in col_names)
                    placeholders = ", ".join(["?" for _ in col_names])
                    insert_sql = f"INSERT INTO {self.settings.schema_name}.[{table_name}] ({columns}) VALUES ({placeholders})"
                    for row in pa_table.to_pylist():
                        values = [row[col] for col in col_names]
                        cursor.execute("SAVE TRANSACTION _row_load")
                        try:
                            cursor.execute(insert_sql, values)
                            loaded += 1
                        except Exception as e:
                            cursor.execute("ROLLBACK TRANSACTION _row_load")
                            logger.warning(f"Skipped row in {table_name}: {e}")
                            skipped += 1
                else:
                    delimiter = self._get_delimiter()
                    with open(str(file_path), "r", encoding="utf-8", newline="") as f:
                        reader = csv.reader(f, delimiter=delimiter)
                        headers = next(reader)
                        columns = ", ".join(f"[{col}]" for col in headers)
                        placeholders = ", ".join(["?" for _ in headers])
                        insert_sql = f"INSERT INTO {self.settings.schema_name}.[{table_name}] ({columns}) VALUES ({placeholders})"
                        for line_no, row in enumerate(reader, start=2):
                            if len(row) < len(headers):
                                row += [None] * (len(headers) - len(row))
                            elif len(row) > len(headers):
                                row = row[: len(headers)]
                            cursor.execute("SAVE TRANSACTION _row_load")
                            try:
                                cursor.execute(insert_sql, row)
                                loaded += 1
                            except Exception as e:
                                cursor.execute("ROLLBACK TRANSACTION _row_load")
                                logger.warning(f"Skipped row {line_no} in {table_name}: {e}")
                                skipped += 1
                conn.commit()
            finally:
                cursor.close()
        finally:
            conn.close()

        logger.info(f"Row-by-row load of {table_name}: {loaded} loaded, {skipped} skipped")
