"""Unit tests for the test CLI command."""

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from omop_lite.cli.commands.database.test import test_command
from omop_lite.settings import Settings


class TestTestCommand:
    """Test cases for the test CLI command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def app(self):
        """Create the test command app."""
        return test_command()

    def test_test_command_default_arguments(self, runner, app):
        """Test test command with default arguments."""
        with (
            patch(
                "omop_lite.cli.commands.database.test._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.test.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "Database Test Results" in result.output
            assert "Database Connection" in result.output
            assert "Schema Check" in result.output
            assert "Basic Operations" in result.output
            assert "✅ PASS" in result.output

    def test_test_command_custom_arguments(self, runner, app):
        """Test test command with custom arguments."""
        with (
            patch(
                "omop_lite.cli.commands.database.test._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.test.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db

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

    def test_test_command_schema_exists(self, runner, app):
        """Test test command when schema exists."""
        with (
            patch(
                "omop_lite.cli.commands.database.test._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.test.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_db.schema_exists.return_value = True
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "Schema 'test_schema' exists" in result.output

    def test_test_command_schema_not_exists(self, runner, app):
        """Test test command when schema does not exist."""
        with (
            patch(
                "omop_lite.cli.commands.database.test._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.test.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_db.schema_exists.return_value = False
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "Schema 'test_schema' does not exist (normal)" in result.output

    def test_test_command_database_error(self, runner, app):
        """Test test command when database connection fails."""
        with (
            patch(
                "omop_lite.cli.commands.database.test._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.test.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.side_effect = Exception("Connection failed")

            result = runner.invoke(app)

            assert result.exit_code == 1
            assert "Database test failed" in result.output
            assert "Connection failed" in result.output

    def test_test_command_settings_creation_error(self, runner, app):
        """Test test command when settings creation fails."""
        with patch(
            "omop_lite.cli.commands.database.test._create_settings"
        ) as mock_create_settings:
            mock_create_settings.side_effect = Exception("Invalid settings")

            result = runner.invoke(app)

            assert result.exit_code == 1

    def test_test_command_environment_variables(self, runner, app):
        """Test test command with environment variables."""
        with (
            patch(
                "omop_lite.cli.commands.database.test._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.test.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
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

    def test_test_command_cli_args_override_env_vars(self, runner, app):
        """Test that CLI arguments override environment variables."""
        with (
            patch(
                "omop_lite.cli.commands.database.test._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.test.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
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

    def test_test_command_success_messages(self, runner, app):
        """Test that appropriate success messages are displayed."""
        with (
            patch(
                "omop_lite.cli.commands.database.test._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.test.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "Database test completed successfully" in result.output
            assert "Connected to test_db" in result.output

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
        return db
