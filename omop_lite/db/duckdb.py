import logging
from importlib.abc import Traversable
from importlib.resources import files
from pathlib import Path

from sqlalchemy import MetaData, create_engine, text

from omop_lite.settings import Settings

from .base import Database, SqlBatchResult

logger = logging.getLogger(__name__)


class DuckDBDatabase(Database):
    """Database implementation for DuckDB.

    Unlike PostgreSQL/SQL Server, DuckDB is an embedded, file-based database -
    there is no server to connect to. `db_name` is repurposed as the path to
    the `.duckdb` file to create/use, and `db_host`/`db_port`/`db_user`/
    `db_password` are ignored.

    SQLAlchemy's reflection (`MetaData.reflect`/`inspect`) emulates
    PostgreSQL's system catalogs via `duckdb-engine`, which is unreliable
    across duckdb/SQLAlchemy versions (e.g. a missing `pg_catalog.pg_collation`
    table). This class avoids that path entirely and queries DuckDB's own
    catalog functions directly where needed.

    DuckDB also has no foreign key support via `ALTER TABLE ... ADD CONSTRAINT`
    (only `PRIMARY KEY` can be added after table creation), so `constraints.sql`
    for this dialect is a no-op - see `add_constraints`.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

        db_path = Path(settings.db_name)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_url = f"duckdb:///{settings.db_name}"
        self.engine = create_engine(self.db_url)
        self.metadata = MetaData(schema=settings.schema_name)
        self.file_path = files(f"omop_lite.scripts.duckdb.{settings.omop_version}")

    def create_schema(self, schema_name: str) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        with self.engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            logger.info(f"Schema '{schema_name}' created.")
            connection.commit()

    def schema_exists(self, schema_name: str) -> bool:
        """Check if a schema exists, via DuckDB's own catalog function.

        Overridden because `inspect(engine).get_schema_names()` goes through
        duckdb-engine's unreliable PostgreSQL-emulation reflection (see class
        docstring).
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        with self.engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1 FROM duckdb_schemas() WHERE schema_name = :schema_name"),
                {"schema_name": schema_name},
            )
            return result.first() is not None

    def tables_exist(self, schema_name: str) -> bool:
        """Check if any OMOP table already exists, via DuckDB's own catalog
        function (see class docstring)."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        with self.engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1 FROM duckdb_tables() WHERE schema_name = :schema_name"),
                {"schema_name": schema_name},
            )
            return result.first() is not None

    def refresh_metadata(self) -> None:
        """No-op for DuckDB.

        The base implementation calls `MetaData.reflect()`, which goes through
        duckdb-engine's unreliable PostgreSQL-emulation reflection (see class
        docstring). Nothing in this class needs reflected metadata.
        """
        return

    def drop_tables(self) -> None:
        """Drop all OMOP tables directly, without relying on reflected metadata."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        with self.engine.connect() as connection:
            for table_name in self.omop_tables:
                connection.execute(
                    text(
                        f"DROP TABLE IF EXISTS {self._quote_identifier(self.settings.schema_name)}."
                        f'"{table_name.lower()}"'
                    )
                )
            connection.commit()
        logger.info("✅ All tables dropped successfully")

    def add_constraints(self) -> SqlBatchResult:
        """Add constraints to the tables in the database.

        DuckDB does not support adding foreign keys to an existing table via
        `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` (only `PRIMARY KEY`
        can be added after creation), so `constraints.sql` for this dialect is
        empty. Foreign key enforcement is skipped entirely for duckdb.
        """
        logger.warning(
            "Foreign key constraints are not supported by DuckDB and were skipped"
        )
        return super().add_constraints()

    def _bulk_load(self, table_name: str, file_path: Path | Traversable) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        delimiter = self._get_delimiter()
        quote = self._get_quote()
        # DuckDB's COPY reads the file itself (no STDIN streaming), so the path
        # goes directly into the SQL text - escape any embedded quotes.
        csv_path = str(file_path).replace("'", "''")

        connection = self.engine.raw_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    f"COPY {self._quote_identifier(self.settings.schema_name)}.{table_name} FROM "
                    f"'{csv_path}' WITH (FORMAT csv, DELIMITER E'{delimiter}', "
                    f"NULL '', QUOTE E'{quote}', HEADER, ENCODING 'utf-8')"
                )
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()
