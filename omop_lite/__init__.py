from omop_lite.settings import settings
from omop_lite.db import Database
import logging


def main() -> None:
    """
    Main function to create the OMOP Lite database.

    This function will create the schema if it doesn't exist,
    create the tables, load the data, and run the update migrations.
    """
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting OMOP Lite")
    logger.debug(f"Settings: {settings.model_dump()}")
    db = Database()

    # Create schema if not exists and not 'public'
    # if settings.schema_name != "public" and db.schema_exists(settings.schema_name):
    #     logger.info(f"Schema '{settings.schema_name}' already exists")
    #     return
    # else:
    #     db.create_schema(settings.schema_name)

    # Create tables
    db.create_tables()

    # Load data
    db.load_data()

    # Add constraints, indices, and primary keys
    db.add_constraints()
    
    logger.info("OMOP Lite database created successfully")


if __name__ == "__main__":
    main()
