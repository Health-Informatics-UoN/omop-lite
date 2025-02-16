#!/bin/bash

# Parse variables
DB_TYPE="$DB_TYPE"

if [ "$DB_TYPE" = "pg" ]; then
    script_dir="/scripts/pg"
elif [ "$DB_TYPE" = "sqlserver" ]; then
    script_dir="/scripts/sql_server"
else
    echo "Invalid DB_TYPE: $DB_TYPE"
    exit 1
fi

echo "Running $DB_TYPE setup script..."

# Run the setup script
bash "$script_dir/init.sh"

echo "OMOP CDM creation finished."
