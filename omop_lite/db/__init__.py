from .base import Database
from .postgres import PostgresDatabase
from .sqlserver import SQLServerDatabase
from omop_lite.settings import Settings


def create_database(settings: Settings) -> Database:
    """Factory function to create the appropriate database instance."""
    if settings.dialect == "postgresql":
        return PostgresDatabase(settings)
    elif settings.dialect == "mssql":
        return SQLServerDatabase(settings)
    else:
        raise ValueError(f"Unsupported dialect: {settings.dialect}")


__all__ = ["Database", "PostgresDatabase", "SQLServerDatabase", "create_database"]
