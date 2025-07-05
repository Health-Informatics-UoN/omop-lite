"""Unit tests for the main CLI entry point."""

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from omop_lite.cli.main import app, main_cli


class TestMainCLI:
    """Test cases for the main CLI entry point."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    def test_main_cli_help(self, runner):
        """Test that the main CLI shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Get an OMOP CDM database running quickly" in result.output
        assert "test" in result.output
        assert "create-tables" in result.output
        assert "load-data" in result.output
        assert "drop" in result.output

    def test_main_cli_default_command(self, runner):
        """Test the default command (no subcommand specified)."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
            patch("omop_lite.cli.main.version") as mock_version,
        ):
            # Mock settings and database
            mock_settings = Mock()
            mock_settings.schema_name = "test_schema"
            mock_settings.db_name = "test_db"
            mock_settings.dialect = "postgresql"
            mock_create_settings.return_value = mock_settings

            mock_db = Mock()
            mock_db.schema_exists.return_value = False
            mock_create_db.return_value = mock_db
            mock_version.return_value = "1.0.0"

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "OMOP Lite" in result.output
            assert "database created successfully" in result.output
            mock_create_settings.assert_called_once()
            mock_create_db.assert_called_once()

    def test_main_cli_default_command_schema_exists(self, runner):
        """Test default command when schema already exists."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
        ):
            mock_settings = Mock()
            mock_settings.schema_name = "test_schema"
            mock_create_settings.return_value = mock_settings

            mock_db = Mock()
            mock_db.schema_exists.return_value = True
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "already exists" in result.output
            mock_db.create_schema.assert_not_called()

    def test_main_cli_default_command_public_schema(self, runner):
        """Test default command with public schema (should not create schema)."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
        ):
            mock_settings = Mock()
            mock_settings.schema_name = "public"
            mock_create_settings.return_value = mock_settings

            mock_db = Mock()
            mock_db.schema_exists.return_value = False
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            mock_db.create_schema.assert_not_called()

    def test_main_cli_with_subcommand(self, runner):
        """Test that subcommands work correctly."""
        # Test drop subcommand
        with (
            patch(
                "omop_lite.cli.commands.database.drop._create_settings"
            ) as mock_create_settings,
            patch(
                "omop_lite.cli.commands.database.drop.create_database"
            ) as mock_create_db,
            patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm,
        ):
            mock_create_settings.return_value = Mock()
            mock_create_db.return_value = Mock()
            mock_confirm.return_value = True

            result = runner.invoke(app, ["drop", "--confirm"])

            assert result.exit_code == 0

    def test_main_cli_environment_variables(self, runner):
        """Test that environment variables are respected."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
        ):
            mock_create_settings.return_value = Mock()
            mock_create_db.return_value = Mock()

            result = runner.invoke(
                app,
                env={
                    "DB_HOST": "env-host",
                    "DB_PORT": "5433",
                    "DB_USER": "env-user",
                    "DB_PASSWORD": "env-password",
                    "DB_NAME": "env-db",
                    "SCHEMA_NAME": "env-schema",
                    "DIALECT": "mssql",
                    "LOG_LEVEL": "DEBUG",
                    "SYNTHETIC": "true",
                    "SYNTHETIC_NUMBER": "500",
                    "DATA_DIR": "env-data",
                    "FTS_CREATE": "true",
                    "DELIMITER": ",",
                },
            )

            assert result.exit_code == 0
            mock_create_settings.assert_called_once()

    def test_main_cli_cli_args_override_env_vars(self, runner):
        """Test that CLI arguments override environment variables."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
        ):
            mock_create_settings.return_value = Mock()
            mock_create_db.return_value = Mock()

            result = runner.invoke(
                app,
                [
                    "--db-host",
                    "cli-host",
                    "--db-user",
                    "cli-user",
                    "--schema-name",
                    "cli-schema",
                ],
                env={
                    "DB_HOST": "env-host",
                    "DB_USER": "env-user",
                    "SCHEMA_NAME": "env-schema",
                },
            )

            assert result.exit_code == 0
            # Verify that CLI args take precedence
            call_args = mock_create_settings.call_args[1]
            assert call_args["db_host"] == "cli-host"
            assert call_args["db_user"] == "cli-user"
            assert call_args["schema_name"] == "cli-schema"

    def test_main_cli_error_handling(self, runner):
        """Test error handling in the main CLI."""
        with patch("omop_lite.cli.main._create_settings") as mock_create_settings:
            mock_create_settings.side_effect = Exception("Configuration error")

            result = runner.invoke(app)

            assert result.exit_code != 0

    def test_main_cli_progress_display(self, runner):
        """Test that progress is displayed during execution."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
        ):
            mock_settings = Mock()
            mock_settings.schema_name = "test_schema"
            mock_create_settings.return_value = mock_settings

            mock_db = Mock()
            mock_db.schema_exists.return_value = False
            mock_create_db.return_value = mock_db

            result = runner.invoke(app)

            assert result.exit_code == 0
            # Check that progress-related text is in output
            assert "Creating tables" in result.output or "Loading data" in result.output

    def test_main_cli_version_display(self, runner):
        """Test that version information is displayed."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
            patch("omop_lite.cli.main.version") as mock_version,
        ):
            mock_create_settings.return_value = Mock()
            mock_create_db.return_value = Mock()
            mock_version.return_value = "2.1.0"

            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "2.1.0" in result.output

    def test_main_cli_synthetic_data_options(self, runner):
        """Test synthetic data options."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
        ):
            mock_create_settings.return_value = Mock()
            mock_create_db.return_value = Mock()

            result = runner.invoke(app, ["--synthetic", "--synthetic-number", "1000"])

            assert result.exit_code == 0
            call_args = mock_create_settings.call_args[1]
            assert call_args["synthetic"] is True
            assert call_args["synthetic_number"] == 1000

    def test_main_cli_fts_options(self, runner):
        """Test full-text search options."""
        with (
            patch("omop_lite.cli.main._create_settings") as mock_create_settings,
            patch("omop_lite.cli.main.create_database") as mock_create_db,
        ):
            mock_create_settings.return_value = Mock()
            mock_create_db.return_value = Mock()

            result = runner.invoke(app, ["--fts-create", "--delimiter", ";"])

            assert result.exit_code == 0
            call_args = mock_create_settings.call_args[1]
            assert call_args["fts_create"] is True
            assert call_args["delimiter"] == ";"

    def test_main_cli_dialect_validation(self, runner):
        """Test dialect validation."""
        with patch("omop_lite.cli.main._create_settings") as mock_create_settings:
            mock_create_settings.side_effect = Exception(
                "dialect must be either 'postgresql' or 'mssql'"
            )

            result = runner.invoke(app, ["--dialect", "invalid"])

            assert result.exit_code != 0

    def test_main_cli_function_entry_point(self, runner):
        """Test the main_cli function entry point."""
        with patch("omop_lite.cli.main.app") as mock_app:
            main_cli()
            mock_app.assert_called_once()

    def test_main_cli_subcommand_help(self, runner):
        """Test help for individual subcommands."""
        # Test drop command help
        result = runner.invoke(app, ["drop", "--help"])
        assert result.exit_code == 0
        assert "Drop tables and/or schema from the database" in result.output

        # Test test command help
        result = runner.invoke(app, ["test", "--help"])
        assert result.exit_code == 0
        assert "test" in result.output.lower()

    def test_main_cli_invalid_subcommand(self, runner):
        """Test behavior with invalid subcommand."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0
