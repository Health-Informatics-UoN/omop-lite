# Installation

OMOP Lite can be installed in several ways depending on your needs and environment.

## Prerequisites

- Python 3.13 or higher
- A database server (PostgreSQL or SQL Server)
- Docker (optional, for containerized deployment)

## Installation Methods

### 1. PyPI Installation (Recommended)

The easiest way to install OMOP Lite is via pip:

```bash
pip install omop-lite
```

### 2. Development Installation

If you want to contribute to OMOP Lite or need the latest development version:

```bash
# Clone the repository
git clone https://github.com/Health-Informatics-UoN/omop-lite.git
cd omop-lite

# Install in development mode with all dependencies
pip install -e ".[dev,test]"
```

### 3. Using uv (Fast Python Package Manager)

If you're using `uv` for Python package management:

```bash
# Install from PyPI
uv add omop-lite

# Or install in development mode
uv sync --dev
```

### 4. Docker Installation

If you prefer to use Docker, you can pull the official image:

```bash
docker pull ghcr.io/health-informatics-uon/omop-lite
```

## Database Setup

### PostgreSQL

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS (using Homebrew)
   brew install postgresql
   
   # Windows
   # Download from https://www.postgresql.org/download/windows/
   ```

2. **Create a database**:
   ```bash
   createdb omop
   ```

### SQL Server

1. **Install SQL Server** (if not already installed):
   - Download from [Microsoft's website](https://www.microsoft.com/en-us/sql-server/sql-server-downloads)
   - Or use Docker: `docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=YourPassword123" -p 1433:1433 mcr.microsoft.com/mssql/server:2019-latest`

2. **Create a database**:
   ```sql
   CREATE DATABASE omop;
   ```

## Verification

After installation, verify that OMOP Lite is working correctly:

```bash
# Check if the CLI is available
omop-lite --help

# Test database connection (adjust parameters as needed)
omop-lite test --db-host localhost --db-name omop
```

## Next Steps

- **[Quick Start](quick-start.md)** - Get up and running with your first OMOP database
- **[Configuration](configuration.md)** - Learn about all configuration options
- **[CLI Reference](../user-guide/cli-reference.md)** - Complete command-line interface documentation 