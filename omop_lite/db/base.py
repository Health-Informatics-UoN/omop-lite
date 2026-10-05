from abc import ABC, abstractmethod
from dataclasses import dataclass
from sqlalchemy import MetaData, inspect, Engine
from pathlib import Path
from typing import Union, Optional
import logging
import re
from importlib.resources import files
from importlib.abc import Traversable
from omop_lite.settings import Settings
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")


def _split_sql_statements(sql: str) -> list[str]:
    """
    Split a SQL script into individual statements, stripping comments
    first.

    Verified safe for the bundled CDM scripts - no ';' or comment markers
    ('--', '/* */') appear inside string literals there, so this simple
    approach doesn't need a real SQL parser.
    """
    sql = _BLOCK_COMMENT_RE.sub("", sql)
    sql = _LINE_COMMENT_RE.sub("", sql)
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


@dataclass
class SqlBatchResult:
    """How many statements in a batch (e.g. constraints.sql) succeeded vs
    failed. A failed statement doesn't block the others - see
    Database._apply_sql_statements."""

    succeeded: int
    failed: int

    @property
    def total(self) -> int:
        return self.succeeded + self.failed


# I thought about having a COMMON_TABLES list, but I think that's trying to be too clever
OMOP_TABLES = {
        "omop5_5": [
            "CARE_SITE",
            "CDM_SOURCE",
            "COHORT",
            "COHORT_DEFINITION",
            "CONCEPT",
            "CONCEPT_ANCESTOR",
            "CONCEPT_CLASS",
            "CONCEPT_METADATA",
            "CONCEPT_RELATIONSHIP",
            "CONCEPT_RELATIONSHIP_METADATA",
            "CONCEPT_SYNONYM",
            "CONDITION_ERA",
            "CONDITION_OCCURRENCE",
            "COST",
            "DEATH",
            "DEVICE_EXPOSURE",
            "DOMAIN",
            "DOSE_ERA",
            "DRUG_ERA",
            "DRUG_EXPOSURE",
            "DRUG_STRENGTH",
            "EPISODE",
            "EPISODE_EVENT",
            "FACT_RELATIONSHIP",
            "LOCATION",
            "MEASUREMENT",
            "METADATA",
            "NOTE",
            "NOTE_NLP",
            "OBSERVATION",
            "OBSERVATION_PERIOD",
            "PACK_CONTENT",
            "PAYER_PLAN_PERIOD",
            "PERSON",
            "PROCEDURE_OCCURRENCE",
            "PROVIDER",
            "RELATIONSHIP",
            "SOURCE_TO_CONCEPT_MAP",
            "SPECIMEN",
            "VISIT_DETAIL",
            "VISIT_OCCURRENCE",
            "VOCABULARY",
        ],
        "omop5_4": [
            "CARE_SITE",
            "CDM_SOURCE",
            "COHORT",
            "COHORT_DEFINITION",
            "CONCEPT",
            "CONCEPT_ANCESTOR",
            "CONCEPT_CLASS",    
            "CONCEPT_RELATIONSHIP",
            "CONCEPT_SYNONYM",
            "CONDITION_ERA",
            "CONDITION_OCCURRENCE",
            "COST",
            "DEATH",
            "DEVICE_EXPOSURE",
            "DOMAIN",
            "DOSE_ERA",
            "DRUG_ERA",
            "DRUG_EXPOSURE",
            "DRUG_STRENGTH",
            "EPISODE",
            "EPISODE_EVENT",
            "FACT_RELATIONSHIP",
            "LOCATION",
            "MEASUREMENT",
            "METADATA",
            "NOTE",
            "NOTE_NLP",
            "OBSERVATION",
            "OBSERVATION_PERIOD",
            "PAYER_PLAN_PERIOD",
            "PERSON",
            "PROCEDURE_OCCURRENCE",
            "PROVIDER",
            "RELATIONSHIP",
            "SOURCE_TO_CONCEPT_MAP",
            "SPECIMEN",
            "VISIT_DETAIL",
            "VISIT_OCCURRENCE",
            "VOCABULARY",
        ],
        "omop5_3": [
            "ATTRIBUTE_DEFINITION",
            "CARE_SITE",
            "CDM_SOURCE",
            "COHORT_DEFINITION",
            "CONCEPT",
            "CONCEPT_ANCESTOR",
            "CONCEPT_CLASS",
            "CONCEPT_RELATIONSHIP",
            "CONCEPT_SYNONYM",
            "CONDITION_ERA",
            "CONDITION_OCCURRENCE",
            "COST",
            "DEATH",
            "DRUG_EXPOSURE",
            "DOMAIN",
            "DEVICE_EXPOSURE",
            "DOSE_ERA",
            "DRUG_ERA",
            "DRUG_STRENGTH",
            "FACT_RELATIONSHIP",
            "LOCATION",
            "MEASUREMENT",
            "METADATA",
            "NOTE",
            "NOTE_NLP",
            "OBSERVATION",
            "OBSERVATION_PERIOD",
            "PAYER_PLAN_PERIOD",
            "PERSON",
            "PROCEDURE_OCCURRENCE",
            "PROVIDER",
            "RELATIONSHIP",
            "SOURCE_TO_CONCEPT_MAP",
            "SPECIMEN",
            "VISIT_DETAIL",
            "VISIT_OCCURRENCE",
            "VOCABULARY",
        ]
        }

class Database(ABC):
    """Abstract base class for database operations"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: Optional[Engine] = None
        self.metadata: Optional[MetaData] = None
        self.file_path: Optional[Union[Path, Traversable]] = None
        self.omop_tables: list[str] = OMOP_TABLES[settings.omop_version]

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

    def refresh_metadata(self) -> None:
        """Refresh the metadata for the database.

        extend_existing re-reflects tables already known to metadata too,
        not just newly-discovered ones - otherwise constraints added via
        raw SQL after the first reflect (e.g. add_constraints's foreign
        keys) would never be picked up, and drop_tables (which computes its
        drop order from this metadata) could then try to drop a table
        before another table that still has a live FK referencing it.
        """
        if not self.metadata or not self.engine:
            raise RuntimeError("Database not properly initialized")
        self.metadata.reflect(bind=self.engine, extend_existing=True)

    def schema_exists(self, schema_name: str) -> bool:
        """Check if a schema exists in the database."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        inspector = inspect(self.engine)
        return schema_name in inspector.get_schema_names()

    def tables_exist(self, schema_name: str) -> bool:
        """Check if any of the OMOP tables already exist in this schema.

        Used by the default pipeline to detect a schema a previous run
        already populated, so re-running (e.g. on every container restart
        under docker-compose) doesn't try to redo create_tables/load_data
        against existing tables - which would either crash on duplicate
        objects, or silently duplicate data.
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        inspector = inspect(self.engine)
        existing = {
            name.lower() for name in inspector.get_table_names(schema=schema_name)
        }
        return any(table.lower() in existing for table in self.omop_tables)

    def create_tables(self) -> None:
        """Create the tables in the database."""
        self._execute_sql_file(self.file_path.joinpath("ddl.sql"))
        self.refresh_metadata()

    def add_primary_keys(self) -> SqlBatchResult:
        """Add primary keys to the tables in the database."""
        return self._apply_sql_statements(self.file_path.joinpath("primary_keys.sql"))

    def add_constraints(self) -> SqlBatchResult:
        """Add constraints to the tables in the database."""
        result = self._apply_sql_statements(self.file_path.joinpath("constraints.sql"))
        self.refresh_metadata()
        return result

    def add_indices(self) -> SqlBatchResult:
        """Add indices to the tables in the database."""
        return self._apply_sql_statements(self.file_path.joinpath("indices.sql"))

    def add_all_constraints(self) -> SqlBatchResult:
        """Add all constraints, primary keys, and indices to the tables in the database.

        This is a convenience method that calls all three constraint methods.
        """
        primary_keys = self.add_primary_keys()
        constraints = self.add_constraints()
        indices = self.add_indices()
        return SqlBatchResult(
            succeeded=primary_keys.succeeded + constraints.succeeded + indices.succeeded,
            failed=primary_keys.failed + constraints.failed + indices.failed,
        )

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
            if self.dialect in ("postgresql", "duckdb"):
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

        if self.settings.synthetic:
            if self.settings.synthetic_number == 1000:
                return files("omop_lite.synthetic.1000")
            elif self.settings.synthetic_number == 1001:
                return files("omop_lite.synthetic.1001")
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
            if self.settings.synthetic_number == 1000 or self.settings.synthetic_number == 1001:
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
            if self.settings.synthetic_number == 1000 or self.settings.synthetic_number == 1001:
                return '"'
        return "\b"

    def _quote_identifier(self, name: str) -> str:
        """
        Quote a schema/table identifier for this dialect.

        Unquoted identifiers are case-folded to lower-case by postgres and
        duckdb, which silently diverges from the exact-case schema that
        create_schema (which already quotes) created.
        """
        if self.dialect == "mssql":
            return f"[{name}]"
        return f'"{name}"'

    def _execute_sql_file(self, file_path: Union[str, Traversable]) -> None:
        """
        Execute a SQL file directly.
        Common implementation for all databases.
        """
        if isinstance(file_path, Traversable):
            file_path = str(file_path)

        with open(file_path, "r") as f:
            sql = f.read().replace(
                "@cdmDatabaseSchema", self._quote_identifier(self.settings.schema_name)
            )

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
                try:
                    connection.rollback()
                except Exception:
                    # Some drivers (e.g. duckdb) raise if there's no active
                    # transaction to roll back - the original error above is
                    # what matters, so don't let this mask it.
                    pass
                raise
            finally:
                cursor.close()
        finally:
            connection.close()

    def _apply_sql_statements(
        self, file_path: Union[str, Traversable]
    ) -> SqlBatchResult:
        """
        Execute each statement in a SQL file independently, continuing past
        a failed statement instead of aborting the whole file.

        Real OMOP vocabulary data routinely doesn't satisfy every foreign
        key (a trimmed vocabulary subset missing some referenced concept,
        for example). Treating the whole file as one transaction - which
        _execute_sql_file does - would let a single such gap roll back
        every other independent constraint/index too. Each statement is
        logged and counted on failure, not silently dropped, and every
        other statement still gets its chance to apply.
        """
        if isinstance(file_path, Traversable):
            file_path = str(file_path)

        with open(file_path, "r") as f:
            sql = f.read().replace(
                "@cdmDatabaseSchema", self._quote_identifier(self.settings.schema_name)
            )

        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        statements = _split_sql_statements(sql)
        succeeded = 0
        failed = 0

        connection = self.engine.raw_connection()
        try:
            cursor = connection.cursor()
            try:
                for statement in statements:
                    try:
                        cursor.execute(statement)
                        connection.commit()
                        succeeded += 1
                    except Exception as e:
                        logger.error(
                            f"Error executing statement in {file_path}: {str(e)}"
                        )
                        try:
                            connection.rollback()
                        except Exception:
                            # See _execute_sql_file - some drivers raise if
                            # there's no active transaction to roll back.
                            pass
                        failed += 1
            finally:
                cursor.close()
        finally:
            connection.close()

        return SqlBatchResult(succeeded=succeeded, failed=failed)
