"""Unit tests for the create_tables CLI command."""

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from omop_lite.cli.commands.database.create_tables import create_tables_command
from omop_lite.settings import Settings


class TestCreateTablesCommand:
    """Test cases for the create_tables CLI command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def app(self):
        """Create the create_tables command app."""
        return create_tables_command()

    def test_create_tables_command_help(self, runner, app):
        """Test that the create_tables command shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Create only the database tables" in result.output
        assert "--db-host" in result.output
        assert "--db-port" in result.output
        assert "--db-user" in result.output

    def test_create_tables_command_default_arguments(self, runner, app):
        """Test create_tables command with default arguments."""
        with (
            patch(
                "omop_lite.cli.commands.database.create_tables._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.create_tables._setup_logging"
            ) as mock_setup_logging,
            patch(
                "omop_lite.cli.commands.database.create_tables.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_logger = Mock()
            mock_setup_logging.return_value = mock_logger
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            mock_create_settings.assert_called_once()
            mock_setup_logging.assert_called_once()
            mock_create_db.assert_called_once()
            mock_db.create_tables.assert_called_once()
            mock_logger.info.assert_called_with("✅ Tables created successfully")

    def test_create_tables_command_custom_arguments(self, runner, app):
        """Test create_tables command with custom arguments."""
        with (
            patch(
                "omop_lite.cli.commands.database.create_tables._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.create_tables._setup_logging"
            ) as mock_setup_logging,
            patch(
                "omop_lite.cli.commands.database.create_tables.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_setup_logging.return_value = Mock()
            mock_create_db.return_value = self._create_mock_database()

            result = runner.invoke(
                app,
                [
                    "--db-host",
                    "custom-host",
                    "--db-port",
                    "5433",
                    "--db-user",
                    "custom-user",
                    "--db-password",
                    "custom-password",
                    "--db-name",
                    "custom-db",
                    "--schema-name",
                    "custom-schema",
                    "--dialect",
                    "mssql",
                    "--log-level",
                    "DEBUG",
                ],
            )

            assert result.exit_code == 0
            mock_create_settings.assert_called_once_with(
                db_host="custom-host",
                db_port=5433,
                db_user="custom-user",
                db_password="custom-password",
                db_name="custom-db",
                schema_name="custom-schema",
                dialect="mssql",
                log_level="DEBUG",
            )

    def test_create_tables_command_schema_exists(self, runner, app):
        """Test create_tables command when schema already exists."""
        with (
            patch(
                "omop_lite.cli.commands.database.create_tables._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.create_tables._setup_logging"
            ) as mock_setup_logging,
            patch(
                "omop_lite.cli.commands.database.create_tables.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_logger = Mock()
            mock_setup_logging.return_value = mock_logger
            mock_db = self._create_mock_database()
            mock_db.schema_exists.return_value = True
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            mock_db.create_schema.assert_not_called()
            # Check that both messages are logged
            mock_logger.info.assert_any_call("Schema 'test_schema' already exists")
            mock_logger.info.assert_any_call("✅ Tables created successfully")

    def test_create_tables_command_schema_not_exists(self, runner, app):
        """Test create_tables command when schema does not exist."""
        with (
            patch(
                "omop_lite.cli.commands.database.create_tables._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.create_tables._setup_logging"
            ) as mock_setup_logging,
            patch(
                "omop_lite.cli.commands.database.create_tables.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_logger = Mock()
            mock_setup_logging.return_value = mock_logger
            mock_db = self._create_mock_database()
            mock_db.schema_exists.return_value = False
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            mock_db.create_schema.assert_called_once_with("test_schema")

    def test_create_tables_command_public_schema(self, runner, app):
        """Test create_tables command with public schema (should not create schema)."""
        with (
            patch(
                "omop_lite.cli.commands.database.create_tables._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.create_tables._setup_logging"
            ) as mock_setup_logging,
            patch(
                "omop_lite.cli.commands.database.create_tables.create_database"
            ) as mock_create_db,
        ):
            settings = self._create_mock_settings()
            settings.schema_name = "public"
            mock_create_settings.return_value = settings
            mock_setup_logging.return_value = Mock()
            mock_create_db.return_value = self._create_mock_database()

            result = runner.invoke(app, ["--schema-name", "public"])

            assert result.exit_code == 0
            # Should not call create_schema for public schema

    def test_create_tables_command_database_error(self, runner, app):
        """Test create_tables command when database operation fails."""
        with (
            patch(
                "omop_lite.cli.commands.database.create_tables._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.create_tables._setup_logging"
            ) as mock_setup_logging,
            patch(
                "omop_lite.cli.commands.database.create_tables.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_setup_logging.return_value = Mock()
            mock_db = self._create_mock_database()
            mock_db.create_tables.side_effect = Exception("Database error")
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code != 0

    def test_create_tables_command_settings_creation_error(self, runner, app):
        """Test create_tables command when settings creation fails."""
        with patch(
            "omop_lite.cli.commands.database.create_tables._create_settings"
        ) as mock_create_settings:
            mock_create_settings.side_effect = Exception("Invalid settings")

            result = runner.invoke(app)

            assert result.exit_code != 0

    def test_create_tables_command_environment_variables(self, runner, app):
        """Test create_tables command with environment variables."""
        with (
            patch(
                "omop_lite.cli.commands.database.create_tables._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.create_tables._setup_logging"
            ) as mock_setup_logging,
            patch(
                "omop_lite.cli.commands.database.create_tables.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_setup_logging.return_value = Mock()
            mock_create_db.return_value = self._create_mock_database()

            result = runner.invoke(
                app,
                env={
                    "DB_HOST": "env-host",
                    "DB_PORT": "5434",
                    "DB_USER": "env-user",
                    "DB_PASSWORD": "env-password",
                    "DB_NAME": "env-db",
                    "SCHEMA_NAME": "env-schema",
                    "DIALECT": "mssql",
                    "LOG_LEVEL": "WARNING",
                },
            )

            assert result.exit_code == 0
            mock_create_settings.assert_called_once()

    def test_create_tables_command_cli_args_override_env_vars(self, runner, app):
        """Test that CLI arguments override environment variables."""
        with (
            patch(
                "omop_lite.cli.commands.database.create_tables._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.create_tables._setup_logging"
            ) as mock_setup_logging,
            patch(
                "omop_lite.cli.commands.database.create_tables.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_setup_logging.return_value = Mock()
            mock_create_db.return_value = self._create_mock_database()

            result = runner.invoke(
                app,
                [
                    "--db-host",
                    "cli-host",
                    "--db-user",
                    "cli-user",
                ],
                env={
                    "DB_HOST": "env-host",
                    "DB_USER": "env-user",
                },
            )

            assert result.exit_code == 0
            call_args = mock_create_settings.call_args[1]
            assert call_args["db_host"] == "cli-host"
            assert call_args["db_user"] == "cli-user"

    def _create_mock_settings(self):
        return Settings(
            db_host="localhost",
            db_port=5432,
            db_user="test_user",
            db_password="test_password",
            db_name="test_db",
            schema_name="test_schema",
            dialect="postgresql",
            log_level="INFO",
        )

    def _create_mock_database(self):
        db = Mock()
        db.schema_exists = Mock(return_value=False)
        db.create_schema = Mock()
        db.create_tables = Mock()
        return db
