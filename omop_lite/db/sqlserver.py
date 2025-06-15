from sqlalchemy import create_engine, MetaData, text
from importlib.resources import files
import logging
from .base import Database
from omop_lite.settings import settings
from typing import Union
from pathlib import Path
from importlib.abc import Traversable

logger = logging.getLogger(__name__)


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

        delimiter = self._get_delimiter()

        with open(str(file_path), "r") as f:
            csv_headers = next(f).strip().split(delimiter)

            connection = self.engine.raw_connection()
            try:
                cursor = connection.cursor()

                columns = ", ".join(f"[{col}]" for col in csv_headers)
                placeholders = ", ".join(["?" for _ in csv_headers])
                insert_sql = f"INSERT INTO {settings.schema_name}.[{table_name}] ({columns}) VALUES ({placeholders})"

                rows = [
                    line.strip().split(delimiter)
                    + [None] * (len(csv_headers) - len(line.strip().split(delimiter)))
                    for line in f
                ]

                cursor.executemany(insert_sql, rows)
                connection.commit()
                cursor.close()
            finally:
                connection.close()
