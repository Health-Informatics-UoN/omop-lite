from sqlalchemy import create_engine, MetaData, text, inspect
from omop_lite.settings import settings
from pathlib import Path
from typing import Dict, Any, List
import csv
from urllib.parse import urlparse
import logging
from importlib.resources import files

logger = logging.getLogger(__name__)


class Database:
    SUPPORTED_DIALECTS = {
        "postgresql": "PostgreSQL",
    }

    def __init__(self) -> None:
        # TODO: Add support for other dialects
        self.db_url = f"postgresql+psycopg2://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        self.engine = create_engine(self.db_url)
        self.dialect = urlparse(self.db_url).scheme.split("+")[0]

        if self.dialect not in self.SUPPORTED_DIALECTS:
            raise ValueError(f"Unsupported database dialect: {self.dialect}")

        # Create metadata with schema
        self.metadata = MetaData(schema=settings.schema_name)
        self.metadata.reflect(bind=self.engine)

    def refresh_metadata(self) -> None:
        """
        Refresh the metadata to pick up newly created tables.
        """
        self.metadata.reflect(bind=self.engine)

    def schema_exists(self, schema_name: str) -> bool:
        """
        Check if a schema exists using SQLAlchemy's database-agnostic inspect interface.
        """
        inspector = inspect(self.engine)
        return schema_name in inspector.get_schema_names()

    def create_schema(self, schema_name: str) -> None:
        with self.engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            logger.info(f"Schema '{schema_name}' created.")
            connection.commit()

    def _execute_sql_file(
        self, file_path: str, schema_replacement: bool = True
    ) -> None:
        """
        Execute a SQL file directly using psycopg2.

        Args:
            file_path: Path to the SQL file to execute
            schema_replacement: Whether to replace @cdmDatabaseSchema with schema name (default: True)
        """
        with open(file_path, "r") as f:
            sql = f.read()

        if schema_replacement:
            sql = sql.replace("@cdmDatabaseSchema", settings.schema_name)

        connection = self.engine.raw_connection()
        try:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(sql)
                    connection.commit()
                except Exception as e:
                    logger.error(f"Error executing {file_path}: {str(e)}")
                    connection.rollback()
        finally:
            connection.close()

    def create_tables(self) -> None:
        """
        Create the tables in the database by executing the DDL SQL file directly.
        """
        self._execute_sql_file(files("omop_lite.scripts.pg").joinpath("ddl.sql"))
        self.refresh_metadata()

    def add_constraints(self) -> None:
        """
        Add constraints, indices, and primary keys to the tables.
        """
        self._execute_sql_file(files("omop_lite.scripts.pg").joinpath("primary_keys.sql"))
        self._execute_sql_file(files("omop_lite.scripts.pg").joinpath("constraints.sql"))
        self._execute_sql_file(files("omop_lite.scripts.pg").joinpath("indices.sql"))

    def _load_csv_data(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Load data from a CSV file into a list of dictionaries.
        """
        data = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # Clean up empty strings to None for NULL values
                cleaned_row = {k: (v if v != "" else None) for k, v in row.items()}
                data.append(cleaned_row)
        return data

    def load_data(self) -> None:
        """
        Load data from CSV files into the database tables
        using SQLAlchemy's database-agnostic insert functionality.
        """
        omop_tables = [
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
            "VOCABULARY",
            "VISIT_OCCURRENCE",
            "RELATIONSHIP",
            "CONCEPT_CLASS",
            "DOMAIN",
        ]

        data_dir = (
            Path("omop_lite/synthetic")
            if settings.synthetic
            else Path(settings.data_dir)
        )
        logger.info(f"Loading data from {data_dir}")

        for table_name in omop_tables:
            table_lower = table_name.lower()
            csv_file = data_dir / f"{table_name}.csv"

            if not csv_file.exists():
                logger.warning(f"Warning: {csv_file} not found, skipping...")
                continue

            logger.info(f"Loading: {table_name}")

            try:
                # Look up table with schema prefix
                qualified_table = f"{settings.schema_name}.{table_lower}"
                if qualified_table not in self.metadata.tables:
                    logger.error(
                        f"Available tables: {list(self.metadata.tables.keys())}"
                    )
                    raise KeyError(f"Table {qualified_table} not found in metadata")

                table = self.metadata.tables[qualified_table]

                # Load and insert data
                data = self._load_csv_data(csv_file)

                chunk_size = 1000
                with self.engine.connect() as connection:
                    for i in range(0, len(data), chunk_size):
                        chunk = data[i : i + chunk_size]
                        if chunk:
                            connection.execute(table.insert(), chunk)
                    connection.commit()

                logger.info(f"Successfully loaded {table_name}")
            except Exception as e:
                logger.error(f"Error loading {table_name}: {str(e)}")
