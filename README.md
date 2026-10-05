# omop-lite

![MIT License][license-badge]
[![omop-lite Releases][omop-lite-releases-badge]][omop-lite-releases]
[![omop-lite Tests][omop-lite-tests-badge]][omop-lite-tests]
![Python][python-badge]
[![omop-lite Containers][docker-badge]][omop-lite-containers]
[![omop-lite helm][helm-badge]][omop-lite-containers]

A small container to get an OMOP CDM database running quickly, with support for PostgreSQL, SQL Server, and DuckDB.

Drop your data into `data/`, and run the container.

## Configuration

You can configure the container or CLI using environment variables, or the equivalent CLI flag. A CLI flag always overrides its environment variable.

| Environment Variable | CLI Flag                           | Default      | Description                                                                                                   |
| --------------------- | ----------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------- |
| `DB_HOST`             | `--db-host`, `-h`                   | `db`         | The hostname of the database.                                                                                   |
| `DB_PORT`             | `--db-port`, `-p`                   | `5432`       | The port number of the database.                                                                                 |
| `DB_USER`             | `--db-user`, `-u`                   | `postgres`   | The username for the database.                                                                                   |
| `DB_PASSWORD`         | `--db-password`                     | `password`   | The password for the database.                                                                                   |
| `DB_NAME`             | `--db-name`, `-d`                   | `omop`       | The name of the database. For the `duckdb` dialect, this is instead the path to the `.duckdb` file to create/use, e.g. `/data/omop.duckdb`. |
| `DIALECT`             | `--dialect`                         | `postgresql` | The type of database to use: `postgresql`, `mssql`, or `duckdb`.                                                 |
| `OMOP_VERSION`        | `--omop_version`                    | `omop5_4`    | Version of the OMOP CDM schema to load: `omop5_3`, `omop5_4`, or `omop5_5`.                                     |
| `SCHEMA_NAME`         | `--schema-name`                     | `public`     | The name of the schema to be created/used in the database.                                                       |
| `DATA_DIR`            | `--data-dir`                        | `data`       | The directory containing the data CSV files.                                                                     |
| `SYNTHETIC`           | `--synthetic` / `--no-synthetic`    | `false`      | Load synthetic data instead of your own.                                                                         |
| `SYNTHETIC_NUMBER`    | `--synthetic-number`                | `100`        | Size of synthetic data: `100`, `1000`, or `1001` (see [Synthetic Data](#synthetic-data)).                        |
| `DELIMITER`           | `--delimiter`                       | tab          | The delimiter used to separate values in the data files, e.g. `,`.                                               |
| `LOG_LEVEL`           | `--log-level`                       | `INFO`       | Logging verbosity.                                                                                                |
| `FTS_CREATE`          | `--fts-create` / `--no-fts-create`  | `false`      | Create full-text search indexes on the `concept` table (PostgreSQL only).                                        |

> `--fts-create`/`FTS_CREATE` is not currently functional. For full-text and vector search, use the `text-search` Compose profile described in [Text search OMOP](#text-search-omop).

## Usage

### CLI

Install the package, which provides the `omop-lite` command:

```bash
pip install omop-lite
omop-lite --help
```

Running `omop-lite` with no subcommand runs the full pipeline: it creates the schema (if needed), creates the tables, loads the data, and adds constraints. This is the same thing the Docker image and Helm chart run by default.

```bash
# Quick start with bundled synthetic data
omop-lite --synthetic
```

#### Commands

Besides the default pipeline, `omop-lite` has subcommands for running each step on its own - useful for custom workflows, or recovering partway through a failed run:

| Command            | Description                                                 |
| ------------------- | ------------------------------------------------------------- |
| `test`              | Test database connectivity, without changing anything.        |
| `create-tables`     | Create the schema (if needed) and tables, without loading data. |
| `load-data`         | Load data into tables that already exist.                     |
| `add-constraints`   | Add primary keys, foreign keys, and indices.                  |
| `add-primary-keys`  | Add only primary key constraints.                              |
| `add-foreign-keys`  | Add only foreign key constraints.                              |
| `add-indices`       | Add only indices.                                              |
| `drop`              | Drop tables and/or the schema.                                 |
| `help-commands`     | Print this table from the CLI.                                 |

Every subcommand accepts the database connection options from the table above (`--db-host`, `--db-port`, `--db-user`, `--db-password`, `--db-name`, `--schema-name`, `--dialect`, `--log-level`). `--omop_version` is also accepted by every subcommand except `test` and `drop`, since those two don't touch version-specific SQL. `load-data` additionally accepts `--synthetic`, `--synthetic-number`, `--data-dir`, and `--delimiter`; `drop` additionally accepts `--tables-only`, `--schema-only`, and `--confirm`. Run `omop-lite <command> --help` to see a command's exact options.

For example, to set up a database step by step instead of running the full pipeline at once:

```bash
omop-lite test                    # check the connection first
omop-lite create-tables
omop-lite load-data --synthetic
omop-lite add-constraints
```

Or to reload data without recreating the schema:

```bash
omop-lite drop --tables-only --confirm
omop-lite create-tables
omop-lite load-data
```

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
helm install omop-lite oci://ghcr.io/health-informatics-uon/charts/omop-lite --version 0.2.2
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
```

Install with custom values:

```bash
helm install omop-lite omop-lite/omop-lite -f values.yaml
```

### DuckDB

Unlike PostgreSQL/SQL Server, [DuckDB](https://duckdb.org/) is file-based rather than a server you connect to - running omop-lite with `DIALECT=duckdb` creates a single `.duckdb` file, pre-loaded with the OMOP CDM schema and either synthetic or your own data, which you can then open directly with the DuckDB CLI, Python, R, or a notebook.

```bash
docker run -v ./data:/data -e DIALECT=duckdb -e DB_NAME=/data/omop.duckdb -e SYNTHETIC=true ghcr.io/health-informatics-uon/omop-lite
```

or with the bundled compose file:

```bash
docker compose --profile duckdb up
```

`DB_NAME` is repurposed as the output file path for this dialect (see Configuration above) - point it at a path under a mounted volume so the file persists after the container exits. `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD` are ignored.

DuckDB does not support adding foreign keys to an existing table (only primary keys can be added after creation), so foreign key constraints are skipped for this dialect - primary keys and indices are still created as normal.

## Synthetic Data

If you need synthetic data, some is provided in the `synthetic` directory. It provides a small amount of data to load quickly.
To load the synthetic data, run the container with the `SYNTHETIC` environment variable set to `true`.

- 100 is fake data
- 1000 is [Synthea 1k](https://registry.opendata.aws/synthea-omop/) data.
- 1001 is [Synthea 1k](https://registry.opendata.aws/synthea-omop/) data but with Specimen, Death, Device Exposure added in

## Bring Your Own Data

You can provide your own data for loading into the tables by placing your files in the `data/` directory. This should contain `.csv` files matching the data tables (`DRUG_STRENGTH.csv`, `CONCEPT.csv`, etc.).

To match the vocabulary files from Athena, this data should be tab-separated, but as a `.csv` file extension.
You can override the delimiter with `DELIMITER` configuration.

## Text search OMOP

### Full-text search

Adding a tsvector column to the concept table and an index on that column makes full-text search queries on the concept table run much faster.

### Vector search

Postgres does vector search too!

### Enabling text search
To enable these features in omop-lite, you can use the `text-search` profile

```bash
docker compose --profile text-search up
```

To do this, you need to have `text-search/embeddings.parquet`, containing concept_ids and embeddings (an example file is provided).
This uses [pgvector](https://github.com/pgvector/pgvector) to create an `embeddings` table.

## Testing

If you're a developer and want to iterate on omop-lite quickly, there's a small subset of the vocabularies sufficient to build in `synthetic/`.
If you wish to test the vector search, there are matching embeddings in `embeddings/embeddings.parquet`.

[omop-lite-containers]: https://github.com/orgs/Health-Informatics-UoN/packages?repo_name=omop-lite
[omop-lite-releases]: https://github.com/Health-Informatics-UoN/omop-lite/releases
[omop-lite-tests]: https://github.com/Health-Informatics-UoN/omop-lite/actions/workflows/check.test.python.yml
[omop-lite-releases-badge]: https://img.shields.io/github/v/tag/Health-Informatics-UoN/omop-lite
[omop-lite-tests-badge]: https://github.com/Health-Informatics-UoN/omop-lite/actions/workflows/check.test.python.yml/badge.svg

[license-badge]: https://img.shields.io/github/license/health-informatics-uon/omop-lite.svg
[python-badge]: https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white
[docker-badge]: https://img.shields.io/badge/docker-%230db7ed.svg?style=flat-square&logo=docker&logoColor=white
[helm-badge]: https://img.shields.io/badge/Helm-0F1689?logo=helm&logoColor=fff&style=flat-square
