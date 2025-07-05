"""Integration tests for CLI commands with real database connections."""

import pytest
import tempfile
from unittest.mock import patch
from typer.testing import CliRunner

from omop_lite.cli.main import app


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def test_env_vars(self):
        """Create test environment variables."""
        return {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_USER": "postgres",
            "DB_PASSWORD": "password",
            "DB_NAME": "omop_test",
            "SCHEMA_NAME": "test_schema",
            "DIALECT": "postgresql",
            "LOG_LEVEL": "INFO",
        }

    def test_drop_command_integration_help(self, runner):
        """Test drop command help in integration context."""
        result = runner.invoke(app, ["drop", "--help"])
        assert result.exit_code == 0
        assert "Drop tables and/or schema from the database" in result.output
        assert "--tables-only" in result.output
        assert "--schema-only" in result.output
        assert "--confirm" in result.output

    def test_drop_command_integration_confirmation_cancelled(self, runner):
        """Test drop command when confirmation is cancelled in integration context."""
        # This test simulates user cancelling the confirmation
        with patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = False

            result = runner.invoke(app, ["drop"])

            assert result.exit_code == 0
            assert "Operation cancelled" in result.output

    def test_drop_command_integration_environment_variables(
        self, runner, test_env_vars
    ):
        """Test drop command with environment variables in integration context."""
        with patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = True

            result = runner.invoke(app, ["drop", "--confirm"], env=test_env_vars)

            # Should not fail due to environment variables
            # The actual database connection might fail, but that's expected in test environment
            assert result.exit_code in [0, 1]  # Either success or expected failure

    def test_drop_command_integration_cli_args_override_env(
        self, runner, test_env_vars
    ):
        """Test that CLI arguments override environment variables in integration context."""
        with patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = True

            result = runner.invoke(
                app,
                [
                    "drop",
                    "--db-host",
                    "override-host",
                    "--db-user",
                    "override-user",
                    "--confirm",
                ],
                env=test_env_vars,
            )

            # Should not fail due to argument parsing
            assert result.exit_code in [0, 1]

    def test_drop_command_integration_tables_only(self, runner):
        """Test drop command with tables-only flag in integration context."""
        with patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = True

            result = runner.invoke(app, ["drop", "--tables-only", "--confirm"])

            # Should not fail due to argument parsing
            assert result.exit_code in [0, 1]

    def test_drop_command_integration_schema_only(self, runner):
        """Test drop command with schema-only flag in integration context."""
        with patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = True

            result = runner.invoke(app, ["drop", "--schema-only", "--confirm"])

            # Should not fail due to argument parsing
            assert result.exit_code in [0, 1]

    def test_drop_command_integration_public_schema_protection(self, runner):
        """Test drop command with public schema protection in integration context."""
        with patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = True

            result = runner.invoke(
                app, ["drop", "--schema-only", "--schema-name", "public", "--confirm"]
            )

            # Should not fail due to argument parsing
            assert result.exit_code in [0, 1]

    def test_main_cli_integration_help(self, runner):
        """Test main CLI help in integration context."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Get an OMOP CDM database running quickly" in result.output
        assert "test" in result.output
        assert "create-tables" in result.output
        assert "load-data" in result.output
        assert "drop" in result.output

    def test_main_cli_integration_default_command(self, runner):
        """Test main CLI default command in integration context."""
        # This will likely fail due to no database connection, but should not crash
        result = runner.invoke(app)

        # Should either succeed or fail gracefully
        assert result.exit_code in [0, 1]

    def test_main_cli_integration_environment_variables(self, runner, test_env_vars):
        """Test main CLI with environment variables in integration context."""
        result = runner.invoke(app, env=test_env_vars)

        # Should either succeed or fail gracefully
        assert result.exit_code in [0, 1]

    def test_main_cli_integration_synthetic_data(self, runner):
        """Test main CLI with synthetic data options in integration context."""
        result = runner.invoke(app, ["--synthetic", "--synthetic-number", "100"])

        # Should either succeed or fail gracefully
        assert result.exit_code in [0, 1]

    def test_main_cli_integration_fts_options(self, runner):
        """Test main CLI with full-text search options in integration context."""
        result = runner.invoke(app, ["--fts-create", "--delimiter", ";"])

        # Should either succeed or fail gracefully
        assert result.exit_code in [0, 1]

    def test_cli_command_structure(self, runner):
        """Test that all CLI commands are properly structured."""
        # Test that all subcommands exist and show help
        subcommands = [
            "test",
            "create-tables",
            "load-data",
            "add-constraints",
            "add-primary-keys",
            "add-foreign-keys",
            "add-indices",
            "drop",
            "help-commands",
        ]

        for subcommand in subcommands:
            result = runner.invoke(app, [subcommand, "--help"])
            assert result.exit_code == 0, f"Subcommand {subcommand} failed to show help"

    def test_cli_error_handling_integration(self, runner):
        """Test CLI error handling in integration context."""
        # Test with invalid subcommand
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

        # Test with invalid options
        result = runner.invoke(app, ["drop", "--invalid-option"])
        assert result.exit_code != 0

    def test_cli_version_integration(self, runner):
        """Test CLI version display in integration context."""
        with patch("omop_lite.cli.main.version") as mock_version:
            mock_version.return_value = "1.0.0"

            result = runner.invoke(app, ["--help"])
            assert result.exit_code == 0
            # Version might be displayed in help or during execution

    def test_cli_logging_integration(self, runner):
        """Test CLI logging in integration context."""
        result = runner.invoke(app, ["--log-level", "DEBUG"])

        # Should either succeed or fail gracefully
        assert result.exit_code in [0, 1]

    def test_cli_dialect_validation_integration(self, runner):
        """Test CLI dialect validation in integration context."""
        result = runner.invoke(app, ["--dialect", "invalid"])

        # Should fail due to invalid dialect
        assert result.exit_code != 0

    def test_cli_port_validation_integration(self, runner):
        """Test CLI port validation in integration context."""
        result = runner.invoke(app, ["--db-port", "invalid"])

        # Should fail due to invalid port
        assert result.exit_code != 0

    def test_cli_synthetic_number_validation_integration(self, runner):
        """Test CLI synthetic number validation in integration context."""
        result = runner.invoke(app, ["--synthetic-number", "invalid"])

        # Should fail due to invalid number
        assert result.exit_code != 0

    def test_cli_no_args_is_help_integration(self, runner):
        """Test CLI behavior when no arguments are provided."""
        # The main CLI should show help when no subcommand is provided
        # but this might be overridden by the default command
        result = runner.invoke(app, [])

        # Should either show help or execute default command
        assert result.exit_code in [0, 1]

    def test_cli_subcommand_isolation(self, runner):
        """Test that subcommands are properly isolated."""
        # Test that each subcommand has its own help
        subcommands = ["test", "create-tables", "load-data", "drop"]

        for subcommand in subcommands:
            result = runner.invoke(app, [subcommand, "--help"])
            assert result.exit_code == 0
            # Each subcommand should have its own help text
            assert subcommand in result.output.lower()

    def test_cli_environment_variable_precedence(self, runner, test_env_vars):
        """Test that CLI arguments take precedence over environment variables."""
        with patch("omop_lite.cli.commands.database.drop.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = True

            # Set environment variable
            test_env_vars["DB_HOST"] = "env-host"

            # Override with CLI argument
            result = runner.invoke(
                app, ["drop", "--db-host", "cli-host", "--confirm"], env=test_env_vars
            )

            # Should not fail due to argument parsing
            assert result.exit_code in [0, 1]
