"""Unit tests for the drop CLI command."""

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from omop_lite.cli.commands.database.drop import drop_command
from omop_lite.settings import Settings


class TestDropCommand:
    """Test cases for the drop CLI command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def app(self):
        """Create the drop command app."""
        return drop_command()

    def test_drop_command_help(self, runner, app):
        """Test that the drop command shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Drop tables and/or schema from the database" in result.output
        assert "--tables-only" in result.output
        assert "--schema-only" in result.output
        assert "--confirm" in result.output

    def test_drop_command_default_arguments(self, runner, app):
        """Test drop command with default arguments."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.return_value = self._create_mock_database()
            mock_confirm.return_value = True

            result = runner.invoke(app, ["--confirm"])

            assert result.exit_code == 0
            mock_create_settings.assert_called_once()
            mock_create_db.assert_called_once()

    def test_drop_command_custom_arguments(self, runner, app):
        """Test drop command with custom arguments."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.return_value = self._create_mock_database()
            mock_confirm.return_value = True

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
                    "--confirm",
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

    def test_drop_tables_only(self, runner, app):
        """Test dropping tables only."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db
            mock_confirm.return_value = True

            result = runner.invoke(app, ["--tables-only", "--confirm"])

            assert result.exit_code == 0
            mock_db.drop_tables.assert_called_once()
            mock_db.drop_schema.assert_not_called()
            mock_db.drop_all.assert_not_called()

    def test_drop_schema_only(self, runner, app):
        """Test dropping schema only."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            settings = self._create_mock_settings()
            settings.schema_name = "custom_schema"
            mock_create_settings.return_value = settings
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db
            mock_confirm.return_value = True

            result = runner.invoke(
                app, ["--schema-only", "--schema-name", "custom_schema", "--confirm"]
            )

            assert result.exit_code == 0
            mock_db.drop_schema.assert_called_once_with("custom_schema")
            mock_db.drop_tables.assert_not_called()
            mock_db.drop_all.assert_not_called()

    def test_drop_schema_only_public_schema(self, runner, app):
        """Test dropping schema only with public schema (should drop tables instead)."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            settings = self._create_mock_settings()
            settings.schema_name = "public"
            mock_create_settings.return_value = settings
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db
            mock_confirm.return_value = True

            result = runner.invoke(
                app, ["--schema-only", "--schema-name", "public", "--confirm"]
            )

            assert result.exit_code == 0
            mock_db.drop_tables.assert_called_once()
            mock_db.drop_schema.assert_not_called()
            mock_db.drop_all.assert_not_called()

    def test_drop_all(self, runner, app):
        """Test dropping everything (default behavior)."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            settings = self._create_mock_settings()
            settings.schema_name = "custom_schema"
            mock_create_settings.return_value = settings
            mock_db = self._create_mock_database()
            mock_create_db.return_value = mock_db
            mock_confirm.return_value = True

            result = runner.invoke(app, ["--schema-name", "custom_schema", "--confirm"])

            assert result.exit_code == 0
            mock_db.drop_all.assert_called_once_with("custom_schema")

    def test_drop_confirmation_cancelled(self, runner, app):
        """Test drop command when confirmation is cancelled."""
        with patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = False

            result = runner.invoke(app)  # No --confirm flag

            assert result.exit_code == 0
            assert "Operation cancelled" in result.output

    def test_drop_database_error(self, runner, app):
        """Test drop command when database operation fails."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_db = self._create_mock_database()
            mock_db.drop_tables.side_effect = Exception("Database connection failed")
            mock_create_db.return_value = mock_db
            mock_confirm.return_value = True

            result = runner.invoke(app, ["--tables-only", "--confirm"])

            assert result.exit_code == 1
            assert "Drop operation failed" in result.output
            assert "Database connection failed" in result.output

    def test_drop_settings_creation_error(self, runner, app):
        """Test drop command when settings creation fails."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.side_effect = Exception("Invalid settings")
            mock_confirm.return_value = True

            result = runner.invoke(app, ["--confirm"])

            assert result.exit_code == 1

    def test_drop_command_environment_variables(self, runner, app):
        """Test drop command with environment variables."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.return_value = self._create_mock_database()
            mock_confirm.return_value = True

            result = runner.invoke(
                app,
                ["--confirm"],
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
            # Verify that environment variables are used when no CLI args provided
            mock_create_settings.assert_called_once()

    def test_drop_command_cli_args_override_env_vars(self, runner, app):
        """Test that CLI arguments override environment variables."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.return_value = self._create_mock_database()
            mock_confirm.return_value = True

            result = runner.invoke(
                app,
                ["--db-host", "cli-host", "--db-user", "cli-user", "--confirm"],
                env={
                    "DB_HOST": "env-host",
                    "DB_USER": "env-user",
                },
            )

            assert result.exit_code == 0
            # Verify that CLI args take precedence
            call_args = mock_create_settings.call_args[1]
            assert call_args["db_host"] == "cli-host"
            assert call_args["db_user"] == "cli-user"

    def test_drop_command_invalid_dialect(self, runner, app):
        """Test drop command with invalid dialect."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.side_effect = Exception(
                "dialect must be either 'postgresql' or 'mssql'"
            )
            mock_confirm.return_value = True

            result = runner.invoke(app, ["--dialect", "invalid", "--confirm"])

            assert result.exit_code == 1

    def test_drop_command_success_messages(self, runner, app):
        """Test that appropriate success messages are displayed."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.return_value = self._create_mock_settings()
            mock_create_db.return_value = self._create_mock_database()
            mock_confirm.return_value = True

            # Test tables-only success message
            result = runner.invoke(
                app, ["--tables-only", "--schema-name", "test_schema", "--confirm"]
            )
            assert result.exit_code == 0
            assert (
                "All tables in schema 'test_schema' dropped successfully"
                in result.output
            )

            # Test schema-only success message
            settings = self._create_mock_settings()
            settings.schema_name = "custom_schema"
            mock_create_settings.return_value = settings

            result = runner.invoke(
                app, ["--schema-only", "--schema-name", "custom_schema", "--confirm"]
            )
            assert result.exit_code == 0
            assert "Schema 'custom_schema' dropped successfully" in result.output

            # Test drop-all success message
            result = runner.invoke(app, ["--schema-name", "custom_schema", "--confirm"])
            assert result.exit_code == 0
            assert "Database completely dropped" in result.output

    def test_drop_command_warning_messages(self, runner, app):
        """Test that appropriate warning messages are displayed."""
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            settings = self._create_mock_settings()
            settings.schema_name = "public"
            mock_create_settings.return_value = settings
            mock_create_db.return_value = self._create_mock_database()
            mock_confirm.return_value = True

            result = runner.invoke(
                app, ["--schema-only", "--schema-name", "public", "--confirm"]
            )
            assert result.exit_code == 0
            assert (
                "Cannot drop 'public' schema, dropping tables instead" in result.output
            )

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
        db.drop_tables = Mock()
        db.drop_schema = Mock()
        db.drop_all = Mock()
        return db
