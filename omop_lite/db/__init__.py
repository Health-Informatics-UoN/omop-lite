from .base import Database
from .postgres import PostgresDatabase
from .sqlserver import SQLServerDatabase
from omop_lite.settings import settings


def create_database() -> Database:
    """Factory function to create the appropriate database instance."""
    if settings.dialect == "postgresql":
        return PostgresDatabase()
    elif settings.dialect == "mssql":
        return SQLServerDatabase()
    else:
        raise ValueError(f"Unsupported dialect: {settings.dialect}")


__all__ = ["Database", "PostgresDatabase", "SQLServerDatabase", "create_database"]
