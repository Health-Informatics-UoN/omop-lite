from abc import ABC, abstractmethod
from sqlalchemy import create_engine, MetaData, text, inspect, Engine
from omop_lite.settings import settings
from pathlib import Path
from typing import Union, Optional
import logging
from importlib.resources import files
from importlib.abc import Traversable

logger = logging.getLogger(__name__)


class Database(ABC):
    """Abstract base class for database operations"""

    def __init__(self) -> None:
        self.engine: Optional[Engine] = None
        self.metadata: Optional[MetaData] = None
        self.file_path: Optional[Union[Path, Traversable]] = None
        self.omop_tables = [
            "CDM_SOURCE",
            "DRUG_STRENGTH",
            "CONCEPT",
            "CONCEPT_RELATIONSHIP",
            "CONCEPT_ANCESTOR",
            "CONCEPT_SYNONYM",
            "CONDITION_ERA",
            "CONDITION_OCCURRENCE",
            "DEATH",
            "DRUG_ERA",
            "DRUG_EXPOSURE",
            "DRUG_STRENGTH",
            "LOCATION",
            "MEASUREMENT",
            "OBSERVATION",
            "OBSERVATION_PERIOD",
            "PERSON",
            "PROCEDURE_OCCURRENCE",
        ]

    @abstractmethod
    def create_schema(self, schema_name: str) -> None:
        """Create a new schema."""
        pass

    @abstractmethod
    def _bulk_load(self, table_name: str, file_path: Union[Path, Traversable]) -> None:
        """Bulk load data into a table."""
        pass

    def _file_exists(self, file_path: Union[Path, Traversable]) -> bool:
        """Check if a file exists, handling both Path and Traversable types."""
        if isinstance(file_path, Traversable):
            return file_path.is_file()
        return file_path.exists()

    def refresh_metadata(self) -> None:
        if not self.metadata or not self.engine:
            raise RuntimeError("Database not properly initialized")
        self.metadata.reflect(bind=self.engine)

    def schema_exists(self, schema_name: str) -> bool:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        inspector = inspect(self.engine)
        return schema_name in inspector.get_schema_names()

    def create_tables(self) -> None:
        self._execute_sql_file(self.file_path.joinpath("ddl.sql"))
        self.refresh_metadata()

    def add_constraints(self) -> None:
        self._execute_sql_file(self.file_path.joinpath("primary_keys.sql"))
        self._execute_sql_file(self.file_path.joinpath("constraints.sql"))
        self._execute_sql_file(self.file_path.joinpath("indices.sql"))

    def load_data(self) -> None:
        """Load data into tables."""
        data_dir = self._get_data_dir()
        logger.info(f"Loading data from {data_dir}")

        for table_name in self.omop_tables:
            table_lower = table_name.lower()
            csv_file = data_dir / f"{table_name}.csv"

            if not self._file_exists(csv_file):
                logger.warning(f"Warning: {csv_file} not found, skipping...")
                continue

            logger.info(f"Loading: {table_name}")

            try:
                self._bulk_load(table_lower, csv_file)
                logger.info(f"Successfully loaded {table_name}")
            except Exception as e:
                logger.error(f"Error loading {table_name}: {str(e)}")

    def _get_data_dir(self) -> Union[Path, Traversable]:
        """
        Return the data directory based on the synthetic flag.
        Common implementation for all databases.
        """
        if settings.synthetic:
            return files("omop_lite.synthetic")
        else:
            data_dir = Path(settings.data_dir)
            if not data_dir.exists():
                raise FileNotFoundError(f"Data directory {data_dir} does not exist")
            return data_dir

    def _execute_sql_file(self, file_path: Union[str, Traversable]) -> None:
        """
        Execute a SQL file directly.
        Common implementation for all databases.
        """
        if isinstance(file_path, Traversable):
            file_path = str(file_path)

        with open(file_path, "r") as f:
            sql = f.read().replace("@cdmDatabaseSchema", settings.schema_name)

        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        connection = self.engine.raw_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql)
                connection.commit()
            except Exception as e:
                logger.error(f"Error executing {file_path}: {str(e)}")
                connection.rollback()
            finally:
                cursor.close()
        finally:
            connection.close()


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
        """Add primary keys, constraints, and indices."""
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

        with open(str(file_path), "r") as f:
            connection = self.engine.raw_connection()
            try:
                cursor = connection.cursor()
                try:
                    with open(str(file_path), "r") as f:
                        cursor.copy_expert(
                            f"COPY {settings.schema_name}.{table_name} FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', NULL '', QUOTE E'\b', HEADER, ENCODING 'UTF8')",
                            f,
                        )
                    connection.commit()
                finally:
                    cursor.close()
            finally:
                connection.close()


class SQLServerDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        self.db_url = f"mssql+pyodbc://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
        self.engine = create_engine(self.db_url)
        self.metadata = MetaData(schema=settings.schema_name)
        self.metadata.reflect(bind=self.engine)
        self.file_path = files("omop_lite.scripts.mssql")

    def create_schema(self, schema_name: str) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        with self.engine.connect() as connection:
            connection.execute(text(f"CREATE SCHEMA [{schema_name}]"))
            logger.info(f"Schema '{schema_name}' created.")
            connection.commit()

    def _bulk_load(self, table_name: str, file_path: Union[Path, Traversable]) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        with open(str(file_path), "r") as f:
            csv_headers = next(f).strip().split("\t")

            connection = self.engine.raw_connection()
            try:
                cursor = connection.cursor()

                columns = ", ".join(f"[{col}]" for col in csv_headers)
                placeholders = ", ".join(["?" for _ in csv_headers])
                insert_sql = f"INSERT INTO {settings.schema_name}.[{table_name}] ({columns}) VALUES ({placeholders})"

                rows = [
                    line.strip().split("\t")
                    + [None] * (len(csv_headers) - len(line.strip().split("\t")))
                    for line in f
                ]

                cursor.executemany(insert_sql, rows)
                connection.commit()
                cursor.close()
            finally:
                connection.close()


def create_database() -> Database:
    """Factory function to create the appropriate database instance."""
    if settings.dialect == "postgresql":
        return PostgresDatabase()
    elif settings.dialect == "mssql":
        return SQLServerDatabase()
    else:
        raise ValueError(f"Unsupported dialect: {settings.dialect}")
