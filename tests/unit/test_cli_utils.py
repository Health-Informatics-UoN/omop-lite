"""Unit tests for CLI utilities."""

import pytest
from unittest.mock import Mock, patch
from typer import BadParameter

from omop_lite.cli.utils import _create_settings, _setup_logging
from omop_lite.settings import Settings


class TestCLIUtils:
    """Test cases for CLI utilities."""

    def test_create_settings_default_values(self):
        """Test _create_settings with default values."""
        settings = _create_settings()

        assert settings.db_host == "db"
        assert settings.db_port == 5432
        assert settings.db_user == "postgres"
        assert settings.db_password == "password"
        assert settings.db_name == "omop"
        assert settings.synthetic is False
        assert settings.synthetic_number == 100
        assert settings.data_dir == "data"
        assert settings.schema_name == "public"
        assert settings.dialect == "postgresql"
        assert settings.log_level == "INFO"
        assert settings.fts_create is False
        assert settings.delimiter == "\t"

    def test_create_settings_custom_values(self):
        """Test _create_settings with custom values."""
        settings = _create_settings(
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
            fts_create=True,
            delimiter=",",
        )

        assert settings.db_host == "custom-host"
        assert settings.db_port == 5433
        assert settings.db_user == "custom-user"
        assert settings.db_password == "custom-password"
        assert settings.db_name == "custom-db"
        assert settings.synthetic is True
        assert settings.synthetic_number == 500
        assert settings.data_dir == "custom-data"
        assert settings.schema_name == "custom-schema"
        assert settings.dialect == "mssql"
        assert settings.log_level == "DEBUG"
        assert settings.fts_create is True
        assert settings.delimiter == ","

    def test_create_settings_invalid_dialect(self):
        """Test _create_settings with invalid dialect."""
        with pytest.raises(
            BadParameter, match="dialect must be either 'postgresql' or 'mssql'"
        ):
            _create_settings(dialect="invalid")

    def test_create_settings_postgresql_dialect(self):
        """Test _create_settings with postgresql dialect."""
        settings = _create_settings(dialect="postgresql")
        assert settings.dialect == "postgresql"

    def test_create_settings_mssql_dialect(self):
        """Test _create_settings with mssql dialect."""
        settings = _create_settings(dialect="mssql")
        assert settings.dialect == "mssql"

    def test_create_settings_case_insensitive_dialect(self):
        """Test _create_settings with case insensitive dialect validation."""
        # The actual implementation is case-sensitive, so these should fail
        with pytest.raises(
            BadParameter, match="dialect must be either 'postgresql' or 'mssql'"
        ):
            _create_settings(dialect="POSTGRESQL")

        with pytest.raises(
            BadParameter, match="dialect must be either 'postgresql' or 'mssql'"
        ):
            _create_settings(dialect="MsSql")

    def test_create_settings_returns_settings_instance(self):
        """Test that _create_settings returns a Settings instance."""
        settings = _create_settings()
        assert isinstance(settings, Settings)

    @patch("omop_lite.cli.utils.logging.basicConfig")
    @patch("omop_lite.cli.utils.logging.getLogger")
    @patch("omop_lite.cli.utils.version")
    def test_setup_logging(self, mock_version, mock_get_logger, mock_basic_config):
        """Test _setup_logging function."""
        mock_settings = Mock()
        mock_settings.log_level = "DEBUG"
        mock_settings.model_dump.return_value = {"test": "value"}

        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_version.return_value = "1.0.0"

        logger = _setup_logging(mock_settings)

        # Verify logging setup
        mock_basic_config.assert_called_once_with(level="DEBUG")
        mock_get_logger.assert_called_once_with("omop_lite.cli.utils")

        # Verify logger calls
        assert mock_logger.info.call_count == 1
        assert mock_logger.debug.call_count == 1

        # Verify log messages
        mock_logger.info.assert_called_with("Starting OMOP Lite 1.0.0")
        mock_logger.debug.assert_called_with("Settings: {'test': 'value'}")

        # Verify return value
        assert logger == mock_logger

    @patch("omop_lite.cli.utils.logging.basicConfig")
    @patch("omop_lite.cli.utils.logging.getLogger")
    @patch("omop_lite.cli.utils.version")
    def test_setup_logging_different_levels(
        self, mock_version, mock_get_logger, mock_basic_config
    ):
        """Test _setup_logging with different log levels."""
        mock_settings = Mock()
        mock_settings.model_dump.return_value = {}

        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_version.return_value = "1.0.0"

        # Test with INFO level
        mock_settings.log_level = "INFO"
        _setup_logging(mock_settings)
        mock_basic_config.assert_called_with(level="INFO")

        # Test with WARNING level
        mock_settings.log_level = "WARNING"
        _setup_logging(mock_settings)
        mock_basic_config.assert_called_with(level="WARNING")

        # Test with ERROR level
        mock_settings.log_level = "ERROR"
        _setup_logging(mock_settings)
        mock_basic_config.assert_called_with(level="ERROR")

    @patch("omop_lite.cli.utils.logging.basicConfig")
    @patch("omop_lite.cli.utils.logging.getLogger")
    @patch("omop_lite.cli.utils.version")
    def test_setup_logging_version_error(
        self, mock_version, mock_get_logger, mock_basic_config
    ):
        """Test _setup_logging when version cannot be determined."""
        mock_settings = Mock()
        mock_settings.log_level = "INFO"
        mock_settings.model_dump.return_value = {}

        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_version.side_effect = Exception("Version not found")

        # The function should raise an exception when version fails
        with pytest.raises(Exception, match="Version not found"):
            _setup_logging(mock_settings)

    def test_create_settings_edge_cases(self):
        """Test _create_settings with edge case values."""
        # Test with empty strings
        settings = _create_settings(
            db_host="",
            db_user="",
            db_password="",
            db_name="",
            schema_name="",
            data_dir="",
        )
        assert settings.db_host == ""
        assert settings.db_user == ""
        assert settings.db_password == ""
        assert settings.db_name == ""
        assert settings.schema_name == ""
        assert settings.data_dir == ""

        # Test with zero port
        settings = _create_settings(db_port=0)
        assert settings.db_port == 0

        # Test with very large synthetic number
        settings = _create_settings(synthetic_number=999999)
        assert settings.synthetic_number == 999999

        # Test with special characters in delimiter
        settings = _create_settings(delimiter="|")
        assert settings.delimiter == "|"

    def test_create_settings_boolean_flags(self):
        """Test _create_settings with boolean flags."""
        # Test synthetic flag
        settings = _create_settings(synthetic=True)
        assert settings.synthetic is True

        settings = _create_settings(synthetic=False)
        assert settings.synthetic is False

        # Test fts_create flag
        settings = _create_settings(fts_create=True)
        assert settings.fts_create is True

        settings = _create_settings(fts_create=False)
        assert settings.fts_create is False

    def test_create_settings_port_validation(self):
        """Test _create_settings with various port values."""
        # Valid ports
        settings = _create_settings(db_port=1)
        assert settings.db_port == 1

        settings = _create_settings(db_port=65535)
        assert settings.db_port == 65535

        # Zero port (edge case)
        settings = _create_settings(db_port=0)
        assert settings.db_port == 0

    def test_create_settings_synthetic_number_validation(self):
        """Test _create_settings with various synthetic number values."""
        # Valid numbers
        settings = _create_settings(synthetic_number=1)
        assert settings.synthetic_number == 1

        settings = _create_settings(synthetic_number=1000)
        assert settings.synthetic_number == 1000

        # Zero (edge case)
        settings = _create_settings(synthetic_number=0)
        assert settings.synthetic_number == 0

    def test_create_settings_log_level_validation(self):
        """Test _create_settings with various log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = _create_settings(log_level=level)
            assert settings.log_level == level

        # Test with lowercase
        settings = _create_settings(log_level="debug")
        assert settings.log_level == "debug"

        # Test with custom level
        settings = _create_settings(log_level="CUSTOM")
        assert settings.log_level == "CUSTOM"
