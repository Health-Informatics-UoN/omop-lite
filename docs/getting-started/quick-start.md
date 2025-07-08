# Quick Start

This guide will help you get OMOP Lite up and running in minutes. We'll create an OMOP CDM database using synthetic data for demonstration purposes.

## Prerequisites

Before starting, make sure you have:

- [OMOP Lite installed](installation.md)
- A PostgreSQL or SQL Server database running
- Basic familiarity with command-line tools

## Step 1: Prepare Your Database

### Option A: PostgreSQL (Recommended)

Start PostgreSQL and create a database:

```bash
# Start PostgreSQL service
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS

# Create database
createdb omop
```

### Option B: SQL Server

Start SQL Server and create a database:

```sql
CREATE DATABASE omop;
```

## Step 2: Run OMOP Lite

### Basic Setup (Default Settings)

The simplest way to get started is with default settings:

```bash
omop-lite --synthetic
```

This command will:
- Connect to a PostgreSQL database on `localhost:5432`
- Use database name `omop`
- Load synthetic data with 100 records
- Create all OMOP CDM tables
- Add constraints and indices

### Custom Configuration

If you need to customize the setup:

```bash
omop-lite \
  --db-host localhost \
  --db-port 5432 \
  --db-user postgres \
  --db-password your_password \
  --db-name omop \
  --synthetic \
  --synthetic-number 1000
```

### Environment Variables

You can also use environment variables for configuration:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_NAME=omop
export SYNTHETIC=true
export SYNTHETIC_NUMBER=1000

omop-lite
```

## Step 3: Verify the Setup

Check that your OMOP database was created successfully:

```bash
# Test the database connection
omop-lite test

# Or connect directly to your database
psql -d omop -c "SELECT COUNT(*) FROM person;"
```

You should see output indicating the number of person records in your database.

## Step 4: Explore Your Data

Now you can explore the OMOP CDM tables:

```sql
-- Check available tables
\dt

-- View person data
SELECT * FROM person LIMIT 5;

-- Check concept vocabulary
SELECT vocabulary_id, COUNT(*) 
FROM concept 
GROUP BY vocabulary_id;

-- Look at condition occurrences
SELECT c.concept_name, COUNT(*) 
FROM condition_occurrence co
JOIN concept c ON co.condition_concept_id = c.concept_id
GROUP BY c.concept_name
ORDER BY COUNT(*) DESC
LIMIT 10;
```

## What's Next?

- **[Configuration Guide](configuration.md)** - Learn about all available configuration options
- **[CLI Reference](../user-guide/cli-reference.md)** - Explore all available commands
- **[Synthetic Data](../user-guide/synthetic-data.md)** - Understand the synthetic data structure
- **[Text Search](../user-guide/text-search.md)** - Enable full-text and vector search capabilities

## Troubleshooting

### Common Issues

1. **Connection Refused**: Make sure your database server is running
2. **Authentication Failed**: Check your database credentials
3. **Database Not Found**: Ensure the database exists before running OMOP Lite

### Getting Help

- Check the [Configuration](configuration.md) page for all available options
- Review the [CLI Reference](../user-guide/cli-reference.md) for detailed command documentation
- Open an issue on [GitHub](https://github.com/Health-Informatics-UoN/omop-lite/issues) if you encounter problems 