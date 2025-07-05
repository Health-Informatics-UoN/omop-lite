"""Unit tests for the load_data CLI command."""

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from omop_lite.cli.commands.database.load_data import load_data_command
from omop_lite.settings import Settings


class TestLoadDataCommand:
    """Test cases for the load_data CLI command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def app(self):
        """Create the load_data command app."""
        return load_data_command()

    def test_load_data_command_help(self, runner, app):
        """Test that the load_data command shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Load data into existing tables" in result.output
        assert "--db-host" in result.output
        assert "--synthetic" in result.output
        assert "--synthetic-number" in result.output
        assert "--data-dir" in result.output

    def test_load_data_command_default_arguments(self, runner, app):
        """Test load_data command with default arguments."""
        with (
            patch(
                "omop_lite.cli.commands.database.load_data._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.load_data.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "Data loaded successfully" in result.output
            mock_create_settings.assert_called_once()
            mock_create_db.assert_called_once()
            mock_db.load_data.assert_called_once()

    def test_load_data_command_custom_arguments(self, runner, app):
        """Test load_data command with custom arguments."""
        with (
            patch(
                "omop_lite.cli.commands.database.load_data._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.load_data.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
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
                    "--synthetic",
                    "--synthetic-number",
                    "500",
                    "--data-dir",
                    "custom-data",
                    "--schema-name",
                    "custom-schema",
                    "--dialect",
                    "mssql",
                    "--log-level",
                    "DEBUG",
                    "--delimiter",
                    ",",
                ],
            )

            assert result.exit_code == 0
            mock_create_settings.assert_called_once_with(
                db_host="custom-host",
                db_port=5433,
                db_user="custom-user",
                db_password="custom-password",
                db_name="custom-db",
                synthetic=True,
                synthetic_number=500,
                data_dir="custom-data",
                schema_name="custom-schema",
                dialect="mssql",
                log_level="DEBUG",
                delimiter=",",
            )

    def test_load_data_command_synthetic_data(self, runner, app):
        """Test load_data command with synthetic data options."""
        with (
            patch(
                "omop_lite.cli.commands.database.load_data._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.load_data.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.return_value = self._create_mock_database()

            result = runner.invoke(
                app,
                [
                    "--synthetic",
                    "--synthetic-number",
                    "1000",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_create_settings.call_args[1]
            assert call_args["synthetic"] is True
            assert call_args["synthetic_number"] == 1000

    def test_load_data_command_database_error(self, runner, app):
        """Test load_data command when database operation fails."""
        with (
            patch(
                "omop_lite.cli.commands.database.load_data._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.load_data.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_db.load_data.side_effect = Exception("Database error")
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code != 0

    def test_load_data_command_settings_creation_error(self, runner, app):
        """Test load_data command when settings creation fails."""
        with patch(
            "omop_lite.cli.commands.database.load_data._create_settings"
        ) as mock_create_settings:
            mock_create_settings.side_effect = Exception("Invalid settings")

            result = runner.invoke(app)

            assert result.exit_code != 0

    def test_load_data_command_environment_variables(self, runner, app):
        """Test load_data command with environment variables."""
        with (
            patch(
                "omop_lite.cli.commands.database.load_data._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.load_data.create_database"
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
                    "SYNTHETIC": "true",
                    "SYNTHETIC_NUMBER": "500",
                    "DATA_DIR": "env-data",
                    "SCHEMA_NAME": "env-schema",
                    "DIALECT": "mssql",
                    "LOG_LEVEL": "WARNING",
                    "DELIMITER": ";",
                },
            )

            assert result.exit_code == 0
            mock_create_settings.assert_called_once()

    def test_load_data_command_cli_args_override_env_vars(self, runner, app):
        """Test that CLI arguments override environment variables."""
        with (
            patch(
                "omop_lite.cli.commands.database.load_data._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.load_data.create_database"
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
                    "--synthetic-number",
                    "200",
                ],
                env={
                    "DB_HOST": "env-host",
                    "DB_USER": "env-user",
                    "SYNTHETIC_NUMBER": "500",
                },
            )

            assert result.exit_code == 0
            call_args = mock_create_settings.call_args[1]
            assert call_args["db_host"] == "cli-host"
            assert call_args["db_user"] == "cli-user"
            assert call_args["synthetic_number"] == 200

    def test_load_data_command_success_messages(self, runner, app):
        """Test that appropriate success messages are displayed."""
        with (
            patch(
                "omop_lite.cli.commands.database.load_data._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.load_data.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.return_value = self._create_mock_database()

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "Data loaded successfully" in result.output
            assert "Data Loading Complete" in result.output

    def test_load_data_command_progress_display(self, runner, app):
        """Test that progress is displayed during data loading."""
        with (
            patch(
                "omop_lite.cli.commands.database.load_data._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.load_data.create_database"
            ) as mock_create_db,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.return_value = self._create_mock_database()

            result = runner.invoke(app)

            assert result.exit_code == 0
            # Progress-related text should be in output
            assert "Loading data" in result.output

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
            synthetic=False,
            synthetic_number=100,
            data_dir="data",
            delimiter="\t",
        )

    def _create_mock_database(self):
        db = Mock()
        db.load_data = Mock()
        return db
