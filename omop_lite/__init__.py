from omop_lite.settings import settings
from omop_lite.db import Database
import logging


def main() -> None:
    """
    Main function to create the OMOP Lite database.

    This function will create the schema if it doesn't exist, 
    create the tables, load the data, and run the update migrations.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting OMOP Lite")
    logger.info(f"Settings: {settings.model_dump()}")
    db = Database()

    # Create schema if not exists and not 'public'
    if settings.schema_name != "public" and db.schema_exists(settings.schema_name):
        logger.info(f"Schema '{settings.schema_name}' already exists")
    else:
        db.create_schema(settings.schema_name)

    # Run create table migration
    db.create_tables()

    # Load data
    db.load_data()

    # Run update table migrations
    db.update_tables()


if __name__ == "__main__":
    main()
