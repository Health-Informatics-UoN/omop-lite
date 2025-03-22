from sqlalchemy import create_engine, MetaData, text
from omop_lite.settings import settings
from alembic import command
from alembic.config import Config
from pathlib import Path
from typing import Dict, Any, List
import csv
from urllib.parse import urlparse


class Database:
    SUPPORTED_DIALECTS = {
        'postgresql': 'PostgreSQL',
        'mssql': 'SQL Server',
        'snowflake': 'Snowflake'
    }

    def __init__(self) -> None:
        self.db_url = f"postgresql+psycopg2://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        print(self.db_url)
        self.engine = create_engine(self.db_url)
        self.dialect = urlparse(self.db_url).scheme.split('+')[0]

        if self.dialect not in self.SUPPORTED_DIALECTS:
            raise ValueError(f"Unsupported database dialect: {self.dialect}")

        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)

    def schema_exists(self, schema_name: str) -> bool:
        query = text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name"
        )
        with self.engine.connect() as connection:
            result = connection.execute(query, {"schema_name": schema_name}).scalar()
        return result is not None

    def create_schema(self, schema_name: str) -> None:
        if not self.schema_exists(schema_name):
            with self.engine.connect() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
                print(f"Schema '{schema_name}' created.")
                connection.commit()
        else:
            print(f"Schema '{schema_name}' already exists.")

    def create_tables(self) -> None:
        """
        Run migrations to create tables
        """
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
        command.upgrade(alembic_cfg, "377e674b2401")
        
        # Refresh metadata to pick up newly created tables
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)

    def _load_csv_data(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Load data from a CSV file into a list of dictionaries.
        """
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                # Clean up empty strings to None for NULL values
                cleaned_row = {k: (v if v != '' else None) for k, v in row.items()}
                data.append(cleaned_row)
        return data

    def load_data(self) -> None:
        """
        Load data from CSV files into the database tables
        using SQLAlchemy's database-agnostic insert functionality.
        """
        omop_tables = [
            "CDM_SOURCE", "DRUG_STRENGTH", "CONCEPT", "CONCEPT_RELATIONSHIP",
            "CONCEPT_ANCESTOR", "CONCEPT_SYNONYM", "CONDITION_ERA",
            "CONDITION_OCCURRENCE", "DEATH", "DRUG_ERA", "DRUG_EXPOSURE",
            "DRUG_STRENGTH", "LOCATION", "MEASUREMENT", "OBSERVATION",
            "OBSERVATION_PERIOD", "PERSON", "PROCEDURE_OCCURRENCE",
            "VOCABULARY", "VISIT_OCCURRENCE", "RELATIONSHIP",
            "CONCEPT_CLASS", "DOMAIN"
        ]

        data_dir = Path("synthetic") if settings.synthetic else Path(settings.data_dir)
        print(f"Loading data from {data_dir}")
        
        for table_name in omop_tables:
            table_lower = table_name.lower()
            csv_file = data_dir / f"{table_name}.csv"
            
            if not csv_file.exists():
                print(f"Warning: {csv_file} not found, skipping...")
                continue

            print(f"Loading: {table_name}")
            
            try:
                # Just look up the table by its name without schema prefix
                if table_lower not in self.metadata.tables:
                    print(f"Available tables: {list(self.metadata.tables.keys())}")
                    raise KeyError(f"Table {table_lower} not found in metadata")
                
                table = self.metadata.tables[table_lower]
                
                # Load and insert data
                data = self._load_csv_data(csv_file)
                    
                chunk_size = 1000
                with self.engine.connect() as connection:
                    for i in range(0, len(data), chunk_size):
                        chunk = data[i:i + chunk_size]
                        if chunk:
                            connection.execute(table.insert(), chunk)
                    connection.commit()
                
                print(f"Successfully loaded {table_name}")
            except Exception as e:
                print(f"Error loading {table_name}: {str(e)}")

    def update_tables(self) -> None:
        """
        Run migrations to update tables
        """
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
        command.upgrade(alembic_cfg, "bbf6835f69e1")
        command.upgrade(alembic_cfg, "3da18f79ff7b")
