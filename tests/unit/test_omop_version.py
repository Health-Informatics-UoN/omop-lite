import pytest

from unittest.mock import Mock, patch

from omop_lite.settings import Settings
from omop_lite.db.postgres import PostgresDatabase

@pytest.fixture
def omop_5_4_settings():
    return Settings(
        db_host="localhost",
        db_port=5432,
        db_user="postgres",
        db_password="password",
        db_name="omop",
        schema_name="cdm",
        dialect="postgresql",
        omop_version="omop5_4"
    )

@pytest.fixture
def omop_5_3_settings():
    return Settings(
        db_host="localhost",
        db_port=5432,
        db_user="postgres",
        db_password="password",
        db_name="omop",
        schema_name="cdm",
        dialect="postgresql",
        omop_version="omop5_3"
    )

def test_5_3_db(omop_5_3_settings):
    with (
        patch("omop_lite.db.postgres.create_engine") as mock_create_engine,
        patch("omop_lite.db.postgres.files") as mock_files,
        patch("omop_lite.db.postgres.MetaData") as mock_metadata,
    ):
        # Mock the engine and metadata
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = PostgresDatabase(omop_5_3_settings)

        assert "ATTRIBUTE_DEFINITION" in db.omop_tables
        assert "COHORT" not in db.omop_tables
        assert "EPISODE" not in db.omop_tables
        assert "EPISODE_EVENT" not in db.omop_tables

def test_5_4_db(omop_5_4_settings):
    with (
        patch("omop_lite.db.postgres.create_engine") as mock_create_engine,
        patch("omop_lite.db.postgres.files") as mock_files,
        patch("omop_lite.db.postgres.MetaData") as mock_metadata,
    ):
        # Mock the engine and metadata
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_files.return_value = Mock()
        mock_metadata.return_value = Mock()

        db = PostgresDatabase(omop_5_4_settings)

        assert "ATTRIBUTE_DEFINITION" not in db.omop_tables
        assert "COHORT" in db.omop_tables
        assert "EPISODE" in db.omop_tables
        assert "EPISODE_EVENT" in db.omop_tables
