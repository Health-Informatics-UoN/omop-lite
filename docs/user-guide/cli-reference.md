# CLI Reference

OMOP Lite provides a comprehensive command-line interface for managing OMOP CDM databases. This reference documents all available commands and their options.

## Main Command

### `omop-lite`

The main command that creates a complete OMOP CDM database with tables, data, and constraints.

```bash
omop-lite [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--synthetic`: Use synthetic data (env: `SYNTHETIC`)
- `--synthetic-number INTEGER`: Number of synthetic records (default: `100`, env: `SYNTHETIC_NUMBER`)
- `--data-dir TEXT`: Data directory (default: `data`, env: `DATA_DIR`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--log-level TEXT`: Logging level (default: `INFO`, env: `LOG_LEVEL`)
- `--fts-create`: Create full-text search indexes (env: `FTS_CREATE`)
- `--delimiter TEXT`: CSV delimiter (default: `\t`, env: `DELIMITER`)
- `--help`: Show help message

**Examples:**

```bash
# Basic usage with synthetic data
omop-lite --synthetic

# Custom database configuration
omop-lite \
  --db-host localhost \
  --db-port 5432 \
  --db-user postgres \
  --db-password mypassword \
  --db-name omop \
  --synthetic \
  --synthetic-number 1000

# SQL Server with custom schema
omop-lite \
  --db-host localhost \
  --db-port 1433 \
  --db-user sa \
  --db-password MyPassword123 \
  --db-name omop \
  --dialect mssql \
  --schema-name omop_cdm \
  --synthetic
```

## Subcommands

### `omop-lite test`

Test database connectivity and configuration.

```bash
omop-lite test [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--help`: Show help message

**Examples:**

```bash
# Test default configuration
omop-lite test

# Test custom configuration
omop-lite test \
  --db-host localhost \
  --db-port 5432 \
  --db-user postgres \
  --db-password mypassword \
  --db-name omop
```

### `omop-lite create-tables`

Create OMOP CDM tables without loading data.

```bash
omop-lite create-tables [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--help`: Show help message

**Examples:**

```bash
# Create tables with default settings
omop-lite create-tables

# Create tables in custom schema
omop-lite create-tables \
  --db-host localhost \
  --db-name omop \
  --schema-name omop_cdm
```

### `omop-lite load-data`

Load data into existing OMOP CDM tables.

```bash
omop-lite load-data [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--synthetic`: Use synthetic data (env: `SYNTHETIC`)
- `--synthetic-number INTEGER`: Number of synthetic records (default: `100`, env: `SYNTHETIC_NUMBER`)
- `--data-dir TEXT`: Data directory (default: `data`, env: `DATA_DIR`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--delimiter TEXT`: CSV delimiter (default: `\t`, env: `DELIMITER`)
- `--help`: Show help message

**Examples:**

```bash
# Load synthetic data
omop-lite load-data --synthetic

# Load custom data from directory
omop-lite load-data \
  --db-host localhost \
  --db-name omop \
  --data-dir /path/to/my/omop/data \
  --delimiter ","
```

### `omop-lite add-constraints`

Add constraints to existing OMOP CDM tables.

```bash
omop-lite add-constraints [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--help`: Show help message

**Examples:**

```bash
# Add constraints with default settings
omop-lite add-constraints

# Add constraints to custom schema
omop-lite add-constraints \
  --db-host localhost \
  --db-name omop \
  --schema-name omop_cdm
```

### `omop-lite add-primary-keys`

Add primary keys to existing OMOP CDM tables.

```bash
omop-lite add-primary-keys [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--help`: Show help message

### `omop-lite add-foreign-keys`

Add foreign keys to existing OMOP CDM tables.

```bash
omop-lite add-foreign-keys [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--help`: Show help message

### `omop-lite add-indices`

Add indices to existing OMOP CDM tables.

```bash
omop-lite add-indices [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--help`: Show help message

### `omop-lite drop`

Drop all OMOP CDM tables and data.

```bash
omop-lite drop [OPTIONS]
```

**Options:**

- `--db-host TEXT`: Database host (default: `db`, env: `DB_HOST`)
- `--db-port INTEGER`: Database port (default: `5432`, env: `DB_PORT`)
- `--db-user TEXT`: Database user (default: `postgres`, env: `DB_USER`)
- `--db-password TEXT`: Database password (default: `password`, env: `DB_PASSWORD`)
- `--db-name TEXT`: Database name (default: `omop`, env: `DB_NAME`)
- `--schema-name TEXT`: Database schema name (default: `public`, env: `SCHEMA_NAME`)
- `--dialect TEXT`: Database dialect (default: `postgresql`, env: `DIALECT`)
- `--help`: Show help message

**Warning:** This command will permanently delete all OMOP CDM tables and data.

**Examples:**

```bash
# Drop tables with confirmation
omop-lite drop

# Drop tables in custom schema
omop-lite drop \
  --db-host localhost \
  --db-name omop \
  --schema-name omop_cdm
```

### `omop-lite help-commands`

Show detailed help for all available commands.

```bash
omop-lite help-commands [OPTIONS]
```

**Options:**

- `--help`: Show help message

## Global Options

All commands support these global options:

- `--help`: Show help message and exit
- `--version`: Show version and exit

## Environment Variables

All command-line options can be set using environment variables. See the [Configuration](../getting-started/configuration.md) guide for a complete list.

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Database connection error
- `4`: Permission error

## Examples

### Complete Workflow

```bash
# 1. Test connection
omop-lite test --db-host localhost --db-name omop

# 2. Create tables
omop-lite create-tables --db-host localhost --db-name omop

# 3. Load data
omop-lite load-data --db-host localhost --db-name omop --synthetic

# 4. Add constraints and indices
omop-lite add-constraints --db-host localhost --db-name omop
omop-lite add-indices --db-host localhost --db-name omop
```

### Batch Processing

```bash
#!/bin/bash
# Script to set up multiple OMOP databases

for db_name in omop_dev omop_test omop_prod; do
    echo "Setting up $db_name..."
    omop-lite \
        --db-host localhost \
        --db-name "$db_name" \
        --synthetic \
        --synthetic-number 100
done
```

### Error Handling

```bash
# Test connection before proceeding
if omop-lite test --db-host localhost --db-name omop; then
    echo "Database connection successful"
    omop-lite --db-host localhost --db-name omop --synthetic
else
    echo "Database connection failed"
    exit 1
fi
``` 