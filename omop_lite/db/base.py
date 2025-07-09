from abc import ABC, abstractmethod
from sqlalchemy import MetaData, inspect, Engine
from pathlib import Path
from typing import Union, Optional
import logging
import time
from importlib.resources import files
from importlib.abc import Traversable
from omop_lite.settings import Settings
from omop_lite.config import get_available_tables
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


class Database(ABC):
    """Abstract base class for database operations"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: Optional[Engine] = None
        self.metadata: Optional[MetaData] = None
        self.file_path: Optional[Union[Path, Traversable]] = None
        self.omop_tables = get_available_tables()

    @property
    def dialect(self) -> str:
        """Get the database dialect."""
        return self.settings.dialect

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

    def _wait_for_file(self, file_path: Union[Path, Traversable], max_wait_time: int = 300) -> bool:
        """Wait for a file to exist, but only if synthetic is False.
        
        Args:
            file_path: The file path to wait for
            max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
            
        Returns:
            True if file exists after waiting, False if timeout reached
        """
        # Only wait if synthetic is False
        if self.settings.synthetic:
            return self._file_exists(file_path)
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            if self._file_exists(file_path):
                return True
            logger.info(f"Waiting for {file_path} to exist...")
            time.sleep(5)  # Wait 5 seconds between checks
        
        logger.warning(f"Timeout waiting for {file_path} after {max_wait_time} seconds")
        return False

    def refresh_metadata(self) -> None:
        """Refresh the metadata for the database."""
        if not self.metadata or not self.engine:
            raise RuntimeError("Database not properly initialized")
        self.metadata.reflect(bind=self.engine)

    def schema_exists(self, schema_name: str) -> bool:
        """Check if a schema exists in the database."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        inspector = inspect(self.engine)
        return schema_name in inspector.get_schema_names()

    def create_tables(self) -> None:
        """Create the tables in the database."""
        self._execute_sql_file(self.file_path.joinpath("ddl.sql"))
        self.refresh_metadata()

    def add_primary_keys(self) -> None:
        """Add primary keys to the tables in the database."""
        self._execute_sql_file(self.file_path.joinpath("primary_keys.sql"))

    def add_constraints(self) -> None:
        """Add constraints to the tables in the database."""
        self._execute_sql_file(self.file_path.joinpath("constraints.sql"))

    def add_indices(self) -> None:
        """Add indices to the tables in the database."""
        self._execute_sql_file(self.file_path.joinpath("indices.sql"))

    def add_all_constraints(self) -> None:
        """Add all constraints, primary keys, and indices to the tables in the database.

        This is a convenience method that calls all three constraint methods.
        """
        self.add_primary_keys()
        self.add_constraints()
        self.add_indices()

    def drop_tables(self) -> None:
        """Drop all tables in the database."""
        if not self.metadata or not self.engine:
            raise RuntimeError("Database not properly initialized")

        # Drop all tables in reverse dependency order
        self.metadata.drop_all(bind=self.engine)
        logger.info("✅ All tables dropped successfully")

    def drop_schema(self, schema_name: str) -> None:
        """Drop a schema and all its contents."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        with self.engine.connect() as connection:
            if self.dialect == "postgresql":
                connection.execute(
                    text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                )
            else:  # SQL Server
                connection.execute(text(f"DROP SCHEMA IF EXISTS [{schema_name}]"))
            connection.commit()
            logger.info(f"✅ Schema '{schema_name}' dropped successfully")

    def drop_all(self, schema_name: str) -> None:
        """Drop everything: tables and schema.

        This is a convenience method that drops tables first, then the schema.
        """
        self.drop_tables()
        if schema_name != "public":
            self.drop_schema(schema_name)
        logger.info("✅ Database completely dropped")

    def load_data(self, required_tables: list[str]) -> None:
        """Load data into tables.

        Args:
            required_tables: A list of table names to load. If not provided, all tables will be loaded.
        """
        data_dir = self._get_data_dir()
        logger.info(f"Loading data from {data_dir}")

        # If no required tables are provided, load all tables
        if not required_tables:
            required_tables = self.omop_tables

        # Filter the tables to only include the required tables 
        tables_to_load = [
            table_name
            for table_name in self.omop_tables
            if table_name.lower() in [table.lower() for table in required_tables]
        ]

        for table_name in tables_to_load:
            table_lower = table_name.lower()
            csv_file = data_dir / f"{table_name}.csv"

            # Wait for file to exist if synthetic is False, otherwise just check if it exists
            if not self._wait_for_file(csv_file):
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

        if self.settings.synthetic:
            if self.settings.synthetic_number == 1000:
                return files("omop_lite.synthetic.1000")
            return files("omop_lite.synthetic.100")
        data_dir = Path(self.settings.data_dir)
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory {data_dir} does not exist")
        return data_dir

    def _get_delimiter(self) -> str:
        """
        Return the delimiter based on the dialect.
        Common implementation for all databases.

        - Synthetic 100 is `\t`
        - Synthetic 1000 is `,`
        - Default is `\t`

        This is used to determine the delimiter for the COPY command.
        """
        if self.settings.synthetic:
            if self.settings.synthetic_number == 1000:
                return ","
            return self.settings.delimiter
        else:
            return self.settings.delimiter

    def _get_quote(self) -> str:
        """
        Return the quote based on the dialect.
        Common implementation for all databases.
        """
        if self.settings.synthetic:
            if self.settings.synthetic_number == 1000:
                return '"'
        return "\b"

    def _execute_sql_file(self, file_path: Union[str, Traversable]) -> None:
        """
        Execute a SQL file directly.
        Common implementation for all databases.
        """
        if isinstance(file_path, Traversable):
            file_path = str(file_path)

        with open(file_path, "r") as f:
            sql = f.read().replace("@cdmDatabaseSchema", self.settings.schema_name)

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
