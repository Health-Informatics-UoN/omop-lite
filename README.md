# omop-lite

A small container to get an OMOP CDM database running quickly, with support for both PostgreSQL and SQL Server.

Drop your data into `data/`, and run the container.

## Environment Variables

You can configure the Docker container using the following environment variables:

- `DB_HOST`: The hostname of the database. Default is `db`.
- `DB_PORT`: The port number of the database. Default is `5432`.
- `DB_USER`: The username for the database. Default is `postgres`.
- `DB_PASSWORD`: The password for the database. Default is `password`.
- `DB_NAME`: The name of the database. Default is `omop`.
- `DIALECT`: The type of database to use. Default is `postgresql`, but can also be `mssql`.
- `SCHEMA_NAME`: The name of the schema to be created/used in the database. Default is `public`.
- `DATA_DIR`: The directory containing the data CSV files. Default is `data`.
- `SYNTHETIC`: Load synthetic data (boolean). Default is `false`
- `SYNTHETIC_NUMBER`: Size of synthetic data, `100` or `1000`. Default is `100`.
- `DELIMITER`: The delimiter used to separate data. Default is `tab`, can also be `,`

## Usage

### Docker

`docker run -v ./data:/data ghcr.io/health-informatics-uon/omop-lite`

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

### Helm

To install using Helm:

```bash
# Add the Helm repository
helm repo add omop-lite https://health-informatics-uon.github.io/omop-lite
helm repo update

# Install the chart
helm install omop-lite omop-lite/omop-lite
```

The Helm chart deploys OMOP Lite as a Kubernetes Job that creates an OMOP CDM in a database. You can customise the installation using a values file:

```yaml
# values.yaml
env:
  dbHost: postgres
  dbPort: "5432"
  dbUser: postgres
  dbPassword: postgres
  dbName: omop_helm
  dialect: postgresql
  schemaName: public
  synthetic: "false" 

# Data mounting configuration
data:
  persistentVolumeClaim:
    enabled: true
    create: true
    size: 10Gi
    storageClass: standard
    accessModes:
      - ReadOnlyMany
  
  # Optional: Prepare data from a local directory
  prepare:
    enabled: true
    sourcePath: "/path/to/your/data"  # Path on the node where data is stored
```

Install with custom values:

```bash
helm install omop-lite omop-lite/omop-lite -f values.yaml
```

#### Using Your Own Data

To use your own data with the Helm chart:

1. **Option 1: Use the built-in data preparation**
   - Set `data.prepare.enabled: true`
   - Set `data.prepare.sourcePath` to the path on your node where the data is stored
   - The chart will automatically copy your data to the PVC before running the OMOP Lite job

2. **Option 2: Manual data preparation**
   - Create a PVC (either through the chart or manually)
   - Copy your data to the PVC using kubectl or another method
   - Set `data.persistentVolumeClaim.enabled: true` and provide the PVC name

## Synthetic Data

If you need synthetic data, some is provided in the `synthetic` directory. It provides a small amount of data to load quickly.
To load the synthetic data, run the container with the `SYNTHETIC` environment variable set to `true`.

- 100 is fake data.
- 1000 is [Synthea 1k](https://registry.opendata.aws/synthea-omop/) data.

## Bring Your Own Data

You can provide your own data for loading into the tables by placing your files in the `data/` directory. This should contain `.csv` files matching the data tables (`DRUG_STRENGTH.csv`, `CONCEPT.csv`, etc.).

To match the vocabulary files from Athena, this data should be tab-separated, but as a `.csv` file extension.
You can override the delimiter with `DELIMITER` configuration.

## Setup Script

The `setup.sh` script included in the Docker image will:

1. Create the schema if it does not already exist.
2. Execute the SQL files to set up the database schema, constraints, and indexes.
3. Load data from the `.csv` files located in the `DATA_DIR`.

## Text search OMOP

### Full-text search

Adding a tsvector column to the concept table and an index on that column makes full-text search queries on the concept table run much faster.
This can be configured by setting `FTS_CREATE` to be non-empty in the environment.

### Vector search

Postgres does vector search too!
To enable this on omop-lite, you can compose the `compose-omop-ts.yml` with

```bash
docker compose -f compose-omop-ts.yml
```

To do this, you need to have `embeddings/embeddings.parquet`, containing concept_ids and embeddings.
This uses [pgvector](https://github.com/pgvector/pgvector) to create an `embeddings` table.

## omop-lite testing
If you're a developer and want to iterate on omop-lite quickly, there's a small subset of the vocabularies sufficient to build in `synthetic/`.
If you wish to test the vector search, there are matching embeddings in `embeddings/embeddings.parquet`.
