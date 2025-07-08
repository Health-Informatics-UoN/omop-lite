# Testing

OMOP Lite uses a comprehensive testing strategy to ensure code quality and reliability. This guide covers how to run tests and write new tests for the project.

## Test Structure

The test suite is organized into two main categories:

```
tests/
├── unit/              # Unit tests
│   ├── test_base_database.py
│   ├── test_cli_*.py
│   ├── test_postgres_database.py
│   └── test_sqlserver_database.py
└── integration/       # Integration tests
    ├── conftest.py
    ├── test_cli_integration.py
    └── test_database_integration.py
```

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -e ".[test]"
```

### Basic Test Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=omop_lite

# Run specific test file
pytest tests/unit/test_cli_main.py

# Run tests matching a pattern
pytest -k "test_create_tables"

# Run tests in parallel
pytest -n auto
```

### Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# CLI tests only
pytest tests/unit/test_cli_*.py

# Database tests only
pytest tests/unit/test_*_database.py
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=omop_lite --cov-report=html

# Generate XML coverage report (for CI)
pytest --cov=omop_lite --cov-report=xml

# Show coverage in terminal
pytest --cov=omop_lite --cov-report=term-missing
```

## Writing Tests

### Unit Tests

Unit tests focus on testing individual functions and classes in isolation.

#### CLI Command Tests

```python
import pytest
from typer.testing import CliRunner
from omop_lite.cli.main import app


def test_create_tables_command_help():
    """Test that create-tables command shows help."""
    runner = CliRunner()
    result = runner.invoke(app, ["create-tables", "--help"])
    assert result.exit_code == 0
    assert "Create OMOP CDM tables" in result.output


def test_create_tables_command_with_options():
    """Test create-tables command with custom options."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "create-tables",
        "--db-host", "localhost",
        "--db-name", "test_db"
    ])
    # Add assertions based on expected behavior
    assert result.exit_code in [0, 1]  # May fail if no DB connection
```

#### Database Tests

```python
import pytest
from unittest.mock import Mock, patch
from omop_lite.db.postgres import PostgreSQLDatabase
from omop_lite.settings import Settings


def test_postgres_database_creation():
    """Test PostgreSQL database creation."""
    settings = Settings(
        db_host="localhost",
        db_port=5432,
        db_user="test",
        db_password="test",
        db_name="test",
        dialect="postgresql"
    )
    
    with patch('omop_lite.db.postgres.create_engine') as mock_engine:
        db = PostgreSQLDatabase(settings)
        assert db.settings == settings
        mock_engine.assert_called_once()


def test_create_tables_method():
    """Test create_tables method."""
    settings = Settings(
        db_host="localhost",
        db_port=5432,
        db_user="test",
        db_password="test",
        db_name="test",
        dialect="postgresql"
    )
    
    with patch('omop_lite.db.postgres.create_engine') as mock_engine:
        mock_connection = Mock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_connection
        
        db = PostgreSQLDatabase(settings)
        db.create_tables()
        
        # Verify that SQL was executed
        assert mock_connection.execute.call_count > 0
```

#### Settings Tests

```python
import pytest
from omop_lite.settings import Settings


def test_settings_defaults():
    """Test that settings have correct defaults."""
    settings = Settings()
    assert settings.db_host == "db"
    assert settings.db_port == 5432
    assert settings.db_user == "postgres"
    assert settings.db_name == "omop"
    assert settings.dialect == "postgresql"


def test_settings_custom_values():
    """Test that custom settings are applied correctly."""
    settings = Settings(
        db_host="custom-host",
        db_port=5433,
        db_user="custom-user",
        db_password="custom-password",
        db_name="custom-db",
        dialect="mssql"
    )
    
    assert settings.db_host == "custom-host"
    assert settings.db_port == 5433
    assert settings.db_user == "custom-user"
    assert settings.db_password == "custom-password"
    assert settings.db_name == "custom-db"
    assert settings.dialect == "mssql"
```

### Integration Tests

Integration tests verify that components work together correctly.

#### Database Integration Tests

```python
import pytest
from omop_lite.db import create_database
from omop_lite.settings import Settings


@pytest.mark.integration
def test_database_creation_and_tables():
    """Test that database can be created and tables can be created."""
    settings = Settings(
        db_host="localhost",
        db_port=5432,
        db_user="test_user",
        db_password="test_password",
        db_name="test_omop",
        dialect="postgresql"
    )
    
    db = create_database(settings)
    
    # Test table creation
    db.create_tables()
    
    # Verify tables exist
    with db.engine.connect() as conn:
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%_occurrence'
        """)
        tables = [row[0] for row in result]
        assert "condition_occurrence" in tables
        assert "drug_exposure" in tables


@pytest.mark.integration
def test_data_loading():
    """Test that synthetic data can be loaded."""
    settings = Settings(
        db_host="localhost",
        db_port=5432,
        db_user="test_user",
        db_password="test_password",
        db_name="test_omop",
        dialect="postgresql",
        synthetic=True,
        synthetic_number=100
    )
    
    db = create_database(settings)
    db.create_tables()
    db.load_data()
    
    # Verify data was loaded
    with db.engine.connect() as conn:
        result = conn.execute("SELECT COUNT(*) FROM person")
        count = result.scalar()
        assert count > 0
```

#### CLI Integration Tests

```python
import pytest
from typer.testing import CliRunner
from omop_lite.cli.main import app


@pytest.mark.integration
def test_full_cli_workflow():
    """Test the complete CLI workflow."""
    runner = CliRunner()
    
    # Test help
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    
    # Test subcommand help
    result = runner.invoke(app, ["create-tables", "--help"])
    assert result.exit_code == 0
    
    result = runner.invoke(app, ["load-data", "--help"])
    assert result.exit_code == 0


@pytest.mark.integration
def test_cli_with_synthetic_data():
    """Test CLI with synthetic data flag."""
    runner = CliRunner()
    
    # This test may fail if no database is available
    result = runner.invoke(app, [
        "--synthetic",
        "--synthetic-number", "100",
        "--db-host", "localhost",
        "--db-name", "test_omop"
    ])
    
    # Accept either success or failure (depends on DB availability)
    assert result.exit_code in [0, 1]
```

## Test Fixtures

### Database Fixtures

```python
import pytest
from omop_lite.settings import Settings
from omop_lite.db import create_database


@pytest.fixture
def test_settings():
    """Provide test database settings."""
    return Settings(
        db_host="localhost",
        db_port=5432,
        db_user="test_user",
        db_password="test_password",
        db_name="test_omop",
        dialect="postgresql"
    )


@pytest.fixture
def test_database(test_settings):
    """Provide a test database instance."""
    return create_database(test_settings)


@pytest.fixture
def clean_database(test_database):
    """Provide a clean database with tables created."""
    test_database.create_tables()
    yield test_database
    # Cleanup could be added here if needed
```

### CLI Fixtures

```python
import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Provide a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def app():
    """Provide the main CLI app."""
    from omop_lite.cli.main import app
    return app
```

## Test Configuration

### pytest.ini

The project includes a `pytest.ini` configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "--disable-warnings",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow running tests",
]
```

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_function():
    """Unit test."""
    pass


@pytest.mark.integration
def test_integration_function():
    """Integration test."""
    pass


@pytest.mark.slow
def test_slow_function():
    """Slow running test."""
    pass
```

Run tests by marker:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Mocking and Patching

### Database Connections

```python
import pytest
from unittest.mock import patch, Mock


def test_database_connection_mock():
    """Test database connection with mocked engine."""
    with patch('omop_lite.db.postgres.create_engine') as mock_engine:
        mock_connection = Mock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_connection
        
        # Your test code here
        db = PostgreSQLDatabase(settings)
        db.create_tables()
        
        # Verify interactions
        mock_engine.assert_called_once()
        assert mock_connection.execute.call_count > 0
```

### File System Operations

```python
import pytest
from unittest.mock import patch, mock_open


def test_file_loading():
    """Test file loading with mocked file system."""
    mock_data = "concept_id,concept_name\n1,Test Concept"
    
    with patch('builtins.open', mock_open(read_data=mock_data)):
        # Your test code here
        pass
```

## Continuous Integration

### GitHub Actions

The project uses GitHub Actions for continuous integration. Tests are run on:

- Python 3.13
- Multiple operating systems (Linux, macOS, Windows)
- Both PostgreSQL and SQL Server databases

### Local CI

Run the full CI suite locally:

```bash
# Install all dependencies
pip install -e ".[dev,test]"

# Run all checks
pre-commit run --all-files
pytest --cov=omop_lite --cov-report=xml
mypy omop_lite/
```

## Best Practices

1. **Test Naming**: Use descriptive test names that explain what is being tested
2. **Arrange-Act-Assert**: Structure tests with clear sections
3. **Isolation**: Each test should be independent and not rely on other tests
4. **Mocking**: Mock external dependencies to keep tests fast and reliable
5. **Coverage**: Aim for high test coverage, especially for critical paths
6. **Documentation**: Add docstrings to test functions explaining the test purpose

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure test database is running and accessible
2. **Import Errors**: Make sure all dependencies are installed
3. **Path Issues**: Use absolute imports and proper path handling
4. **Mock Issues**: Ensure mocks are properly configured and cleaned up

### Debug Mode

Run tests with debug output:

```bash
pytest -v -s --tb=long
```

This will show print statements and full tracebacks for debugging. 