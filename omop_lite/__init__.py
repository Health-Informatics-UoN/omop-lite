from omop_lite.settings import settings
from omop_lite.db import create_database
import logging
from importlib.metadata import version


def main() -> None:
    """
    Main function to create the OMOP Lite database.

    This function will create the schema if it doesn't exist,
    create the tables, load the data, and run the update migrations.
    """
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting OMOP Lite {version('omop-lite')}")
    logger.debug(f"Settings: {settings.model_dump()}")
    db = create_database()

    # Handle schema creation if not using 'public'
    if settings.schema_name != "public":
        if db.schema_exists(settings.schema_name):
            logger.info(f"Schema '{settings.schema_name}' already exists")
            return
        else:
            db.create_schema(settings.schema_name)

    # Continue with table creation, data loading, etc.
    db.create_tables()
    db.load_data()
    db.add_constraints()

    logger.info("OMOP Lite database created successfully")


if __name__ == "__main__":
    main()
