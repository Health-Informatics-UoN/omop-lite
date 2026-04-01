import csv
import io
from sqlalchemy import create_engine, MetaData, text
from importlib.resources import files
import logging
import pyarrow.csv as pa_csv
import pyarrow.parquet as pq
from .base import Database, DataFormat
from omop_lite.settings import Settings
from typing import Union
from pathlib import Path
from importlib.abc import Traversable

logger = logging.getLogger(__name__)


class PostgresDatabase(Database):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.db_url = f"postgresql+psycopg2://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        self.engine = create_engine(self.db_url)
        self.metadata = MetaData(schema=settings.schema_name)
        self.metadata.reflect(bind=self.engine)
        self.file_path = files("omop_lite.scripts.pg")

    def create_schema(self, schema_name: str) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        with self.engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            logger.info(f"Schema '{schema_name}' created.")
            connection.commit()

    def add_constraints(self) -> None:
        """
        Add primary keys, constraints, and indices.

        Override to add full-text search.
        """
        super().add_constraints()
        self._add_full_text_search()

    def _add_full_text_search(self) -> None:
        """Add full-text search capabilities to the concept table."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        if not self.settings.fts_create:
            logger.info("Full-text search creation disabled")
            return

        logger.info("Adding full-text search on concept table")

        # Add the tsvector column
        fts_sql = files("omop_lite.scripts").joinpath("fts.sql")
        self._execute_sql_file(fts_sql)
        logger.info("Added full-text search column")

        # Create the GIN index
        fts_index_sql = self.file_path.joinpath("fts_index.sql")
        self._execute_sql_file(fts_index_sql)
        logger.info("Created full-text search index")

    def _bulk_load(
        self, table_name: str, file_path: Union[Path, Traversable], fmt: DataFormat
    ) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        try:
            connection = self.engine.raw_connection()
            try:
                cursor = connection.cursor()
                try:
                    if fmt == DataFormat.PARQUET:
                        buf = io.BytesIO()
                        pa_csv.write_csv(pq.read_table(str(file_path)), buf)
                        buf.seek(0)
                        cursor.copy_expert(
                            f"COPY {self.settings.schema_name}.{table_name} FROM STDIN WITH (FORMAT csv, HEADER, ENCODING 'UTF8')",
                            buf,
                        )
                    else:
                        delimiter = self._get_delimiter()
                        quote = self._get_quote()
                        with open(str(file_path), "r") as f:
                            cursor.copy_expert(
                                f"COPY {self.settings.schema_name}.{table_name} FROM STDIN WITH (FORMAT csv, DELIMITER E'{delimiter}', NULL '', QUOTE E'{quote}', HEADER, ENCODING 'UTF8')",
                                f,
                            )
                    connection.commit()
                finally:
                    cursor.close()
            finally:
                connection.close()
        except Exception as e:
            if not self.settings.skip_bad_rows:
                raise
            logger.warning(
                f"Bulk load failed for {table_name}: {e}. "
                "Retrying row-by-row (this may be slow for large files)."
            )
            self._row_load(table_name, file_path, fmt)

    def _row_load(
        self, table_name: str, file_path: Union[Path, Traversable], fmt: DataFormat
    ) -> None:
        """Row-by-row fallback that skips invalid rows using savepoints."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        loaded = 0
        skipped = 0
        connection = self.engine.raw_connection()
        try:
            cursor = connection.cursor()
            try:
                if fmt == DataFormat.PARQUET:
                    pa_table = pq.read_table(str(file_path))
                    col_names = pa_table.schema.names
                    columns = ", ".join(f'"{c}"' for c in col_names)
                    placeholders = ", ".join(["%s"] * len(col_names))
                    sql = f'INSERT INTO {self.settings.schema_name}.{table_name} ({columns}) VALUES ({placeholders})'
                    for row in pa_table.to_pylist():
                        values = [row[c] for c in col_names]
                        cursor.execute("SAVEPOINT _row_load")
                        try:
                            cursor.execute(sql, values)
                            cursor.execute("RELEASE SAVEPOINT _row_load")
                            loaded += 1
                        except Exception as e:
                            cursor.execute("ROLLBACK TO SAVEPOINT _row_load")
                            logger.warning(f"Skipped row in {table_name}: {e}")
                            skipped += 1
                else:
                    delimiter = self._get_delimiter()
                    with open(str(file_path), "r", encoding="utf-8") as f:
                        reader = csv.reader(f, delimiter=delimiter)
                        headers = next(reader)
                        columns = ", ".join(f'"{h}"' for h in headers)
                        placeholders = ", ".join(["%s"] * len(headers))
                        sql = f'INSERT INTO {self.settings.schema_name}.{table_name} ({columns}) VALUES ({placeholders})'
                        for line_no, row in enumerate(reader, start=2):
                            if len(row) < len(headers):
                                row += [None] * (len(headers) - len(row))
                            elif len(row) > len(headers):
                                row = row[: len(headers)]
                            values = [v if v != "" else None for v in row]
                            cursor.execute("SAVEPOINT _row_load")
                            try:
                                cursor.execute(sql, values)
                                cursor.execute("RELEASE SAVEPOINT _row_load")
                                loaded += 1
                            except Exception as e:
                                cursor.execute("ROLLBACK TO SAVEPOINT _row_load")
                                logger.warning(f"Skipped row {line_no} in {table_name}: {e}")
                                skipped += 1
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

        logger.info(f"Row-by-row load of {table_name}: {loaded} loaded, {skipped} skipped")
