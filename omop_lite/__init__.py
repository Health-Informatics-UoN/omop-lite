from omop_lite.settings import settings
from omop_lite.db import Database
import logging


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting OMOP Lite")
    db = Database()

    # Create schema if not exists
    # db.create_schema(settings.schema_name)

    # Run create table migration
    db.create_tables()

    # Load data
    db.load_data()

    # Run update table migrations
    db.update_tables()


if __name__ == "__main__":
    main()
