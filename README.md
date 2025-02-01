# omop-lite

A small container to get an OMOP CDM Postgres database running quickly.

Drop your data into `data/`, and run the container.

## Environment Variables

You can configure the Docker container using the following environment variables:

- `DB_HOST`: The hostname of the PostgreSQL database. Default is `db`.
- `DB_PORT`: The port number of the PostgreSQL database. Default is `5432`.
- `DB_USER`: The username for the PostgreSQL database. Default is `postgres`.
- `DB_PASSWORD`: The password for the PostgreSQL database. Default is `password`.
- `DB_NAME`: The name of the PostgreSQL database. Default is `omop`.
- `SCHEMA_NAME`: The name of the schema to be created/used in the database. Default is `omop`.
- `DATA_DIR`: The directory containing the data CSV files. Default is `data`.
- `SYNTHETIC`: Load synthetic data (boolean). Default is `false`

## Usage

`docker run -v ./data:/data ghcr.io/AndyRae/omop-lite`

```yaml
# docker-compose.yml
services:
  omop-lite:
    image: ghcr.io/health-informatics-uon/omop-lite
    volumes:
      - ./data:/data
    depends_on:
      - db

  db:
    image: postgres:latest
    environment:
      - POSTGRES_DB=omop
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
```

## Synthetic Data

If you need synthetic data, some is provided in the `synthetic` directory. It provides a small amount of data to load quickly.
To load the synthetic data, run the container with the `SYNTHETIC` environment variable set to `true`.

This data only provides the following tables:

- `CONCEPT`
- `CONDITION_OCCURRENCE`
- `MEASUREMENT`
- `OBSERVATION`
- `PERSON`

## Bring Your Own Data

You can provide your own data for loading into the tables by placing your files in the `data/` directory. This should contain `.csv` files matching the data tables (`DRUG_STRENGTH.csv`, `CONCEPT.csv`, etc.).

To match the vocabulary files from Athena, this data should be tab-separated, but as a `.csv` file extension.

## Setup Script

The `setup.sh` script included in the Docker image will:

1. Create the schema if it does not already exist.
2. Execute the SQL files to set up the database schema, constraints, and indexes.
3. Load data from the `.csv` files located in the `DATA_DIR`.
