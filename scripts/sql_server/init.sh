#!/bin/bash

# Parse variables
DB_HOST="$DB_HOST"
DB_PORT="$DB_PORT"
DB_USER="$DB_USER"
SQL_SERVER_USER="$SQL_SERVER_USER"
DB_PASSWORD="$DB_PASSWORD"
DB_NAME="$DB_NAME"
DATA_DIR="$DATA_DIR"
SCHEMA_NAME="$SCHEMA_NAME"
SYNTHETIC="$SYNTHETIC"

# If synthetic data is requested, use the synthetic data directory
if [ "$SYNTHETIC" = "true" ]; then
    DATA_DIR="/synthetic"
fi

# SQL files
sql_files=(primary_keys.sql constraints.sql indices.sql)
omop_tables=(CDM_SOURCE DRUG_STRENGTH CONCEPT CONCEPT_RELATIONSHIP CONCEPT_ANCESTOR CONCEPT_SYNONYM CONDITION_ERA CONDITION_OCCURRENCE DEATH DRUG_ERA DRUG_EXPOSURE DRUG_STRENGTH LOCATION MEASUREMENT OBSERVATION OBSERVATION_PERIOD PERSON PROCEDURE_OCCURRENCE VOCABULARY VISIT_OCCURRENCE RELATIONSHIP CONCEPT_CLASS DOMAIN)

# Directory paths
script_dir="/scripts/sql_server"
temp_dir="/tmp"

echo "Waiting for the Database.."
if wait4x tcp "$DB_HOST:$DB_PORT" --timeout 60s; then
    echo "Database is up - continuing..."
else
    echo "Failed to connect to the database within the timeout period."
    exit 1
fi

# Check if the schema already exists
schema_exists=$(sqlcmd -S "$DB_HOST,$DB_PORT" -U "$DB_USER" -P "$DB_PASSWORD" -d "$DB_NAME" -h -1 -W -Q "
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = '${SCHEMA_NAME}')
        SELECT 1
    ELSE
        SELECT 0
" | tr -d '[:space:]')

if [ "$schema_exists" = "1" ]; then
    echo "Schema '${SCHEMA_NAME}' already exists. Skipping CDM creation."
    exit 0
fi

echo "Creating schema.."
sqlcmd -S "$DB_HOST,$DB_PORT" -U "$DB_USER" -P "$DB_PASSWORD" -d "$DB_NAME" -Q "
IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = '${SCHEMA_NAME}')
    EXEC('CREATE SCHEMA ${SCHEMA_NAME}')
"

# echo "Creating tables.."
# temp_ddl="${temp_dir}/temp_ddl.sql"
# sed "s/@cdmDatabaseSchema/${SCHEMA_NAME}/g" "${script_dir}/ddl.sql" > "$temp_ddl"
# sqlcmd -S "$DB_HOST" -U "$DB_USER" -P "$DB_PASSWORD" -d "$DB_NAME" -i "$temp_ddl"
# rm "$temp_ddl"

# echo "Loading data.."
# for table in "${omop_tables[@]}"; do
#     echo 'Loading: ' $table
#     table_lower=$(echo "$table" | tr '[:upper:]' '[:lower:]')
#     PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
#         -c "\COPY ${SCHEMA_NAME}.${table_lower} FROM '${DATA_DIR}/${table}.csv' WITH (FORMAT csv, DELIMITER E'\t', NULL '""', QUOTE E'\b', HEADER, ENCODING 'UTF8')"
# done

# # Create pk, constraints, indexes
# for sql_file in "${sql_files[@]}"; do
#     echo "Creating $sql_file.."
#     input_file="${script_dir}/${sql_file}"
#     temp_file="${temp_dir}/temp_${sql_file}"

#     # Replace placeholder
#     sed "s/@cdmDatabaseSchema/${SCHEMA_NAME}/g" "$input_file" > "$temp_file"
#     PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$temp_file"
#     rm "$temp_file"
# done

echo "OMOP CDM creation finished."
