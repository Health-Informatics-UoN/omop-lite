# Contributing

Thank you for your interest in contributing to OMOP Lite! This guide will help you get started with development and contributing to the project.

## Development Setup

### Prerequisites

- Python 3.13 or higher
- Git
- A database (PostgreSQL or SQL Server)
- Docker (optional, for containerized development)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Health-Informatics-UoN/omop-lite.git
   cd omop-lite
   ```

2. **Install dependencies**:
   ```bash
   # Using pip
   pip install -e ".[dev,test]"
   
   # Using uv
   uv sync --dev
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

### Development Environment

The project uses several tools for code quality:

- **Ruff**: Code formatting and linting
- **MyPy**: Type checking
- **Pre-commit**: Git hooks for code quality
- **Pytest**: Testing framework

## Project Structure

```
omop-lite/
├── omop_lite/           # Main package
│   ├── cli/            # Command-line interface
│   ├── db/             # Database abstractions
│   ├── scripts/        # SQL scripts
│   └── synthetic/      # Synthetic data
├── tests/              # Test suite
├── docs/               # Documentation
├── charts/             # Helm charts
└── embeddings/         # Vector embeddings
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the coding standards:

- Use type hints for all functions
- Write docstrings in Google style
- Follow PEP 8 formatting (enforced by Ruff)
- Add tests for new functionality

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=omop_lite

# Run specific test file
pytest tests/unit/test_cli_main.py

# Run integration tests
pytest tests/integration/
```

### 4. Code Quality Checks

```bash
# Format code
ruff format

# Lint code
ruff check

# Type checking
mypy omop_lite/

# Run all checks
pre-commit run --all-files
```

### 5. Build Documentation

```bash
# Build docs locally
mkdocs serve

# Build for production
mkdocs build
```

### 6. Commit and Push

```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/your-feature-name
```

## Coding Standards

### Python Code

- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Use Google-style docstrings for all public functions and classes
- **Imports**: Use absolute imports, organize imports with `isort`
- **Naming**: Use snake_case for variables and functions, PascalCase for classes

### Example Function

```python
from typing import Optional, List
from omop_lite.settings import Settings


def create_database(settings: Settings) -> "Database":
    """Create a database instance based on the provided settings.
    
    Args:
        settings: Database configuration settings.
        
    Returns:
        A configured database instance.
        
    Raises:
        DatabaseError: If the database cannot be created.
    """
    if settings.dialect == "postgresql":
        return PostgreSQLDatabase(settings)
    elif settings.dialect == "mssql":
        return SQLServerDatabase(settings)
    else:
        raise ValueError(f"Unsupported dialect: {settings.dialect}")
```

### SQL Scripts

- Use consistent indentation (2 spaces)
- Include comments for complex queries
- Follow the naming conventions in existing scripts

### Tests

- Write unit tests for all new functionality
- Use descriptive test names
- Mock external dependencies
- Test both success and error cases

## Adding New Features

### 1. CLI Commands

To add a new CLI command:

1. Create a new file in `omop_lite/cli/commands/`
2. Define the command function with proper type hints
3. Add the command to `omop_lite/cli/main.py`
4. Write tests in `tests/unit/test_cli_*.py`

### 2. Database Support

To add support for a new database:

1. Create a new class in `omop_lite/db/`
2. Inherit from `BaseDatabase`
3. Implement all required methods
4. Add tests in `tests/unit/test_*.py`

### 3. Documentation

When adding new features:

1. Update the relevant documentation files
2. Add examples and usage instructions
3. Update the API reference (auto-generated)

## Testing

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With coverage
pytest --cov=omop_lite --cov-report=html
```

### Writing Tests

```python
import pytest
from omop_lite.cli.main import app
from typer.testing import CliRunner


def test_create_tables_command():
    """Test the create-tables command."""
    runner = CliRunner()
    result = runner.invoke(app, ["create-tables", "--help"])
    assert result.exit_code == 0
    assert "Create OMOP CDM tables" in result.output
```

### Test Database

For integration tests, use the provided test database configuration:

```python
import pytest
from omop_lite.settings import Settings


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
```

## Documentation

### Building Documentation

```bash
# Serve locally
mkdocs serve

# Build static site
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy
```

### Documentation Structure

- **User Guide**: How to use OMOP Lite
- **API Reference**: Auto-generated from code
- **Development**: Contributing and development guides

### Adding Documentation

1. Create new markdown files in the appropriate directory
2. Update `mkdocs.yml` navigation
3. Include code examples and explanations
4. Test the documentation locally

## Release Process

### Versioning

The project uses semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. **Update version** in `pyproject.toml`
2. **Update changelog** with new features and fixes
3. **Create release branch**:
   ```bash
   git checkout -b release/v1.2.3
   ```
4. **Run full test suite**:
   ```bash
   pytest
   pre-commit run --all-files
   ```
5. **Build and test package**:
   ```bash
   python -m build
   ```
6. **Create GitHub release** with release notes
7. **Publish to PyPI** (if applicable)

## Getting Help

- **Issues**: Create an issue on GitHub for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Code Review**: All contributions require review before merging

## Code of Conduct

Please be respectful and inclusive in all interactions. The project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/0/code_of_conduct/).

## License

By contributing to OMOP Lite, you agree that your contributions will be licensed under the MIT License. 