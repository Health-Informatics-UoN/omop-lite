# Configuration

OMOP Lite can be configured using command-line arguments, environment variables, or a combination of both. Command-line arguments take precedence over environment variables.

## Configuration Options

### Database Connection

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--db-host` | `DB_HOST` | `db` | Database hostname |
| `--db-port` | `DB_PORT` | `5432` | Database port number |
| `--db-user` | `DB_USER` | `postgres` | Database username |
| `--db-password` | `DB_PASSWORD` | `password` | Database password |
| `--db-name` | `DB_NAME` | `omop` | Database name |
| `--dialect` | `DIALECT` | `postgresql` | Database dialect (`postgresql` or `mssql`) |
| `--schema-name` | `SCHEMA_NAME` | `public` | Database schema name |

### Data Configuration

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--data-dir` | `DATA_DIR` | `data` | Directory containing CSV data files |
| `--synthetic` | `SYNTHETIC` | `false` | Use synthetic data (boolean) |
| `--synthetic-number` | `SYNTHETIC_NUMBER` | `100` | Size of synthetic data (`100` or `1000`) |
| `--delimiter` | `DELIMITER` | `\t` | CSV delimiter (tab or comma) |

### Advanced Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--log-level` | `LOG_LEVEL` | `INFO` | Logging level |
| `--fts-create` | `FTS_CREATE` | `false` | Create full-text search indexes |

## Configuration Examples

### Basic PostgreSQL Setup

```bash
omop-lite \
  --db-host localhost \
  --db-port 5432 \
  --db-user postgres \
  --db-password mypassword \
  --db-name omop \
  --synthetic
```

### SQL Server Setup

```bash
omop-lite \
  --db-host localhost \
  --db-port 1433 \
  --db-user sa \
  --db-password MyPassword123 \
  --db-name omop \
  --dialect mssql \
  --synthetic
```

### Using Environment Variables

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=mypassword
export DB_NAME=omop
export SYNTHETIC=true
export SYNTHETIC_NUMBER=1000
export FTS_CREATE=true

omop-lite
```

### Custom Schema

```bash
omop-lite \
  --db-host localhost \
  --db-name omop \
  --schema-name omop_cdm \
  --synthetic
```

### Custom Data Directory

```bash
omop-lite \
  --db-host localhost \
  --db-name omop \
  --data-dir /path/to/my/omop/data \
  --delimiter ","
```

## Environment Variable Reference

### Database Connection

- **`DB_HOST`**: The hostname or IP address of your database server
- **`DB_PORT`**: The port number your database is listening on
  - PostgreSQL default: `5432`
  - SQL Server default: `1433`
- **`DB_USER`**: Username for database authentication
- **`DB_PASSWORD`**: Password for database authentication
- **`DB_NAME`**: Name of the database to create/use
- **`DIALECT`**: Database type (`postgresql` or `mssql`)
- **`SCHEMA_NAME`**: Schema name within the database

### Data Configuration

- **`DATA_DIR`**: Path to directory containing OMOP CSV files
- **`SYNTHETIC`**: Set to `true` to use built-in synthetic data
- **`SYNTHETIC_NUMBER`**: Size of synthetic dataset (`100` or `1000`)
- **`DELIMITER`**: Character used to separate fields in CSV files
  - `\t` for tab-separated (default for OMOP vocabulary files)
  - `,` for comma-separated

### Advanced Configuration

- **`LOG_LEVEL`**: Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- **`FTS_CREATE`**: Set to `true` to create full-text search indexes

## Configuration Files

While OMOP Lite doesn't currently support configuration files directly, you can create shell scripts or use tools like `direnv` to manage environment variables:

### Using direnv

Create a `.envrc` file in your project directory:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=mypassword
export DB_NAME=omop
export SYNTHETIC=true
```

Then run `direnv allow` to enable the environment variables.

### Shell Script

Create a `setup-omop.sh` script:

```bash
#!/bin/bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=mypassword
export DB_NAME=omop
export SYNTHETIC=true

omop-lite "$@"
```

Make it executable and use it: `./setup-omop.sh`

## Best Practices

1. **Security**: Never hardcode passwords in scripts. Use environment variables or secure credential management.
2. **Environment Separation**: Use different configurations for development, testing, and production.
3. **Documentation**: Document your configuration choices for team members.
4. **Version Control**: Don't commit sensitive configuration to version control.

## Troubleshooting Configuration

### Common Issues

1. **Connection Timeout**: Check `DB_HOST` and `DB_PORT` values
2. **Authentication Failed**: Verify `DB_USER` and `DB_PASSWORD`
3. **Database Not Found**: Ensure the database exists or OMOP Lite has permission to create it
4. **Permission Denied**: Check database user permissions

### Debug Mode

Enable debug logging to troubleshoot configuration issues:

```bash
omop-lite --log-level DEBUG --db-host localhost --db-name omop
``` 