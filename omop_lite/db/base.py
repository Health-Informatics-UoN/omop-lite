from abc import ABC, abstractmethod
from sqlalchemy import MetaData, inspect, Engine
from pathlib import Path
from typing import Union, Optional
import logging
from importlib.resources import files
from importlib.abc import Traversable
from omop_lite.settings import settings

logger = logging.getLogger(__name__)


class Database(ABC):
    """Abstract base class for database operations"""

    def __init__(self) -> None:
        self.engine: Optional[Engine] = None
        self.metadata: Optional[MetaData] = None
        self.file_path: Optional[Union[Path, Traversable]] = None
        self.omop_tables = [
            "CDM_SOURCE",
            "CONCEPT",
            "CONCEPT_ANCESTOR",
            "CONCEPT_CLASS",
            "CONCEPT_RELATIONSHIP",
            "CONCEPT_SYNONYM",
            "CONDITION_ERA",
            "CONDITION_OCCURRENCE",
            "DEATH",
            "DOMAIN",
            "DRUG_ERA",
            "DRUG_EXPOSURE",
            "DRUG_STRENGTH",
            "LOCATION",
            "MEASUREMENT",
            "OBSERVATION",
            "OBSERVATION_PERIOD",
            "PERSON",
            "PROCEDURE_OCCURRENCE",
            "RELATIONSHIP",
            "VISIT_OCCURRENCE",
            "VOCABULARY",
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

    def add_constraints(self) -> None:
        """Add constraints to the tables in the database.
        
        Executes the sql files for the given data directory.
        """
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
            if settings.synthetic_number == 1000:
                return files("omop_lite.synthetic.1000")
            return files("omop_lite.synthetic.100")
        data_dir = Path(settings.data_dir)
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
        if settings.synthetic:
            if settings.synthetic_number == 1000:
                return ","
            return settings.delimiter
        else:
            return settings.delimiter
        
    def _get_quote(self) -> str:
        """
        Return the quote based on the dialect.
        Common implementation for all databases.
        """
        if settings.synthetic:
            if settings.synthetic_number == 1000:
                return '"'
        return '\b'

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
