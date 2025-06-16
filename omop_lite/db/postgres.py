from sqlalchemy import create_engine, MetaData, text
from importlib.resources import files
import logging
from .base import Database
from omop_lite.settings import settings
from typing import Union
from pathlib import Path
from importlib.abc import Traversable

logger = logging.getLogger(__name__)


class PostgresDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        self.db_url = f"postgresql+psycopg2://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        self.engine = create_engine(self.db_url)
        self.metadata = MetaData(schema=settings.schema_name)
        self.metadata.reflect(bind=self.engine)
        self.file_path = files("omop_lite.scripts.pg")

    def create_schema(self, schema_name: str) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        with self.engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
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

        if not settings.fts_create:
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

    def _bulk_load(self, table_name: str, file_path: Union[Path, Traversable]) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        delimiter = self._get_delimiter()
        quote = self._get_quote()

        with open(str(file_path), "r") as f:
            connection = self.engine.raw_connection()
            try:
                cursor = connection.cursor()
                try:
                    with open(str(file_path), "r") as f:
                        cursor.copy_expert(
                            f"COPY {settings.schema_name}.{table_name} FROM STDIN WITH (FORMAT csv, DELIMITER E'{delimiter}', NULL '', QUOTE E'{quote}', HEADER, ENCODING 'UTF8')",
                            f,
                        )
                    connection.commit()
                finally:
                    cursor.close()
            finally:
                connection.close()
