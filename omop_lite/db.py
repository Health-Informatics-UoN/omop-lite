from sqlalchemy import create_engine, MetaData, text
from omop_lite.settings import settings
from alembic import command
from alembic.config import Config
import os


class Database:
    def __init__(self) -> None:
        self.db_url = f"postgresql+psycopg2://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        print(self.db_url)
        self.engine = create_engine(self.db_url)

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

    def load_data_from_directory(self, data_dir: str) -> None:
        # TODO: load data from directory
        pass

    def load_synthetic_data(self) -> None:
        # TODO: load synthetic data
        pass

    def update_tables(self) -> None:
        """
        Run migrations to update tables
        """
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
        command.upgrade(alembic_cfg, "9a343fe1e393")
