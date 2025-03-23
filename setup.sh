#!/bin/bash

# Required variables:
# DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, VOCAB_DATA_DIR, SCHEMA_NAME, SYNTHETIC

if [ "$DB_TYPE" = "pg" ]; then
    script_dir="/scripts/pg"
elif [ "$DB_TYPE" = "sqlserver" ]; then
    script_dir="/scripts/sql_server"
else
    echo "Invalid DB_TYPE: $DB_TYPE"
    exit 1
fi

echo "Running $DB_TYPE setup script..."

# Directory paths
script_dir="/scripts"
temp_dir="/tmp"

echo "Waiting for the Database.."
wait4x postgresql postgres://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?sslmode=disable --timeout 60s
echo "Database is up - continuing.."

# Check if the schema already exists
schema_exists=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM information_schema.schemata WHERE schema_name = '${SCHEMA_NAME}'")

# Check if the schema is `public`
if [ "$SCHEMA_NAME" != "public" ]; then

    # if schema is not `public` and already exists, assume we put it there and have nothing to do
    if [ "$schema_exists" ]; then
        echo "Schema '${SCHEMA_NAME}' already exists. Skipping CDM creation."
        exit 0  # Exit gracefully
    fi

fi

# Create schema only if it doesn't exist (even for `public`, though this should be incredibly rare)
if [ -z "$schema_exists" ]; then
    echo "Creating schema.."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE SCHEMA IF NOT EXISTS ${SCHEMA_NAME};"
fi

echo "Creating tables.."
temp_ddl="${temp_dir}/temp_ddl.sql"
sed "s/@cdmDatabaseSchema/${SCHEMA_NAME}/g" "${script_dir}/ddl.sql" > "$temp_ddl"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$temp_ddl"
rm "$temp_ddl"

echo "Loading data.."
for table in "${omop_tables[@]}"; do
    echo 'Loading: ' $table
    table_lower=$(echo "$table" | tr '[:upper:]' '[:lower:]')
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -c "\COPY ${SCHEMA_NAME}.${table_lower} FROM '${DATA_DIR}/${table}.csv' WITH (FORMAT csv, DELIMITER E'\t', NULL '""', QUOTE E'\b', HEADER, ENCODING 'UTF8')"
done

# Create pk, constraints, indexes
for sql_file in "${sql_files[@]}"; do
    echo "Creating $sql_file.."
    input_file="${script_dir}/${sql_file}"
    temp_file="${temp_dir}/temp_${sql_file}"

    # Replace placeholder
    sed "s/@cdmDatabaseSchema/${SCHEMA_NAME}/g" "$input_file" > "$temp_file"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$temp_file"
    rm "$temp_file"
done

echo "OMOP CDM creation finished."

if [ -n "$FTS_CREATE" ]; then
  echo "Adding full-text search on concept table"
  input_file="${script_dir}/fts.sql"
  temp_file="${temp_dir}/temp_fts.sql"

  sed "s/@cdmDatabaseSchema/${SCHEMA_NAME}/g" "$input_file" > "$temp_file"
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$temp_file"
  rm "$temp_file"
fi
