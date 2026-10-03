# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

omop-lite is a Python CLI/container that provisions an OMOP CDM database (schema, data load, constraints) against either PostgreSQL or SQL Server. It's distributed as a PyPI package (`omop-lite`), a Docker image (`ghcr.io/health-informatics-uon/omop-lite`), and a Helm chart.

## Commands

Package management is `uv`. Python is 3.13 locally (`.python-version`); `requires-python = ">=3.11"` and CI tests 3.11 + 3.13.

```bash
uv sync --all-groups              # install deps (dev + test) — pytest is NOT in the default sync
uv run pytest tests               # run all tests
uv run pytest tests/unit          # unit tests only (no DB required)
uv run pytest tests/integration   # integration tests (require live Postgres AND SQL Server)
uv run pytest tests/unit/test_cli_utils.py::test_name  # single test
uv run ruff check .               # lint
uv run ruff format .              # format
uv run mypy .                     # type check (strict mode, see pyproject.toml)
```

Integration tests read connection settings from env vars (`POSTGRES_DB_HOST`, `POSTGRES_DB_PORT`, `POSTGRES_DB_USERNAME`, `POSTGRES_DB_PASSWORD`, `POSTGRES_DB_DATABASE`, `POSTGRES_DB_SCHEMA`, and the `SQLSERVER_*` equivalents — see `tests/integration/conftest.py`). Note these differ from the runtime env vars (`DB_HOST`, `DB_USER`, …). Every integration test is parametrized over *both* dialects, so a missing SQL Server gives failures, not skips. The `unit`/`integration`/`slow` pytest markers are declared in `pyproject.toml` but not applied to any test — select by path, not by `-m`.

Local databases come from `docker-compose.yml`, which is profile-gated:

```bash
docker compose --profile postgres up      # postgres 18 + omop-lite
docker compose --profile sqlserver up     # mssql 2025 + omop-lite (linux/amd64)
docker compose --profile text-search up   # pgvector + omop-lite + text-search loader
```

### What CI enforces

`check.test.python.yml` runs **only pytest** (both DBs as services). `check.test.system.yml` builds the Docker image and asserts row counts end-to-end (99 persons for synthetic 100, 1130 for synthetic 1000, on both dialects) — if you change loading or DDL, expect this to be the test that catches it. **Neither ruff nor mypy runs in CI**, and the existing tree does not pass either (~56 ruff findings, ~379 mypy errors). So treat clean lint/types as a goal for code you touch, not a baseline you can diff against — scope checks to the files you changed.

Pre-commit runs `ruff --fix` and `ruff format`; install with `pre-commit install` if editing frequently. It pins its own older ruff (`v0.8.6`) than the dev dependency, so its formatting can differ slightly from `uv run ruff format`.

### Releases

`main` pushes run semantic-release (angular preset, `release.config.js`), so **commit messages and PR titles must be Conventional Commits** — a workflow validates PR titles. Versioning is `hatch-vcs` from git tags, so there is no version string to bump manually. Chart version in `charts/omop-lite/Chart.yaml` *is* manual.

## Architecture

**CLI (`omop_lite/cli/`)**: Typer app. `main.py`'s callback is the default (no-subcommand) pipeline: build `Settings` → `create_database` → create schema (if not `public`) → `create_tables` → `load_data` → `add_all_constraints`. Subcommands under `cli/commands/database/` (`test`, `create-tables`, `load-data`, `add-constraints`, `add-primary-keys`, `add-foreign-keys`, `add-indices`, `drop`) expose individual pipeline steps, plus `help-commands` (`cli/commands/help.py`) for a Rich summary table.

**Option duplication is the main maintenance hazard.** Each option is declared as a `typer.Option` in `main.py`'s callback, *again* in every subcommand module that needs it, again as a parameter of `cli/utils.py::_create_settings`, and again as a `Field` in `settings.py`. Adding or renaming one option means touching all of those, plus `README.md`, `charts/omop-lite/values.yaml` and `charts/omop-lite/templates/deployment.yaml`. Existing drift to be aware of: no subcommand exposes `omop_version`, and `_create_settings` always passes it explicitly, so **subcommands silently use `omop5_4` even when `OMOP_VERSION=omop5_3` is set** — only the default pipeline honours it. The Helm chart likewise has no `OMOP_VERSION` or `FTS_CREATE`.

**Settings (`omop_lite/settings.py`)**: `pydantic-settings` `Settings` model is the single source of config truth, loadable from env vars or `.env`, with `extra = "allow"`. `cli/utils.py::_create_settings` bridges CLI args into a `Settings` instance.

**Database layer (`omop_lite/db/`)**: `Database` (`base.py`) is an ABC holding dialect-agnostic logic — table lists (`OMOP_TABLES`, keyed by `"omop5_3"`/`"omop5_4"`), `load_data`, `create_tables`/`add_primary_keys`/`add_constraints`/`add_indices` (all just execute a named `.sql` file via `_execute_sql_file`), and `drop_all`. `PostgresDatabase` and `SQLServerDatabase` (`postgres.py`, `sqlserver.py`) implement `create_schema` and `_bulk_load` per dialect — Postgres uses `COPY ... FROM STDIN`, SQL Server does `pyodbc` row-by-row parameterized `INSERT`s (and pads/trims rows that don't match the header width). `create_database()` in `db/__init__.py` is the dialect factory (`settings.dialect` → class).

**Errors are swallowed, not raised.** `_execute_sql_file` catches every exception, logs it, rolls back, and returns normally; `load_data` catches per-table exceptions and continues; missing table files log a warning and are skipped. A green run therefore does not mean the data or DDL landed — check the log output, and prefer asserting against the database (as the integration and system tests do) when verifying a change.

**There is no separate foreign-keys SQL.** `add-foreign-keys` calls `db.add_constraints()`, the same method `add-constraints` calls, and `add-constraints` additionally runs primary keys and indices. On Postgres, `add_constraints` is overridden to append full-text search.

**Full-text search (`fts_create`) is currently broken.** `PostgresDatabase._add_full_text_search` executes `omop_lite/scripts/fts.sql` and `<version>/fts_index.sql`, but both files were removed in commit `2911dc0` ("Text search profile") when FTS moved to the `text-search/` compose profile. The setting, CLI flag and tests for it remain. Either restore the SQL files or remove the code path — don't assume `--fts-create` works.

**SQL scripts (`omop_lite/scripts/`)**: Static `.sql` files per dialect (`pg/`, `mssql/`) and per OMOP version (`omop5_3/`, `omop5_4/`) — `ddl.sql`, `constraints.sql`, `indices.sql`, `primary_keys.sql`. These are the actual DDL source of truth, not generated. `@cdmDatabaseSchema` placeholders are string-substituted with `settings.schema_name` at execution time (`Database._execute_sql_file`). When changing table structure, edit the SQL files, not Python — and edit all four dialect/version combinations.

**Synthetic data (`omop_lite/synthetic/`)**: Bundled fixture data at three sizes, selected via `synthetic_number` (100 = small fake set, tab-delimited; 1000/1001 = Synthea-derived, comma-delimited, quoted; 1001 adds Specimen/Death/Device Exposure). Delimiter/quote selection lives in `Database._get_delimiter`/`_get_quote` — synthetic-vs-real *and* size both affect parsing, so check there before assuming CSV format is uniform. `load_data` only looks for `<TABLE>.csv`, so the one `.tsv` file in `synthetic/100` is never loaded.

**Data loading contract**: user-supplied data goes in `data/` (or wherever `DATA_DIR` points) as one `.csv` per OMOP table (uppercase table name), matching the delimiter set via `DELIMITER` (default tab, to match Athena vocabulary exports despite the `.csv` extension).

**`text-search/`**: a separate, optional Docker Compose profile that loads a `pgvector` embeddings table from `text-search/embeddings.parquet` for concept vector search — independent of the main omop-lite pipeline.

**Helm chart (`charts/omop-lite/`)**: deploys omop-lite as a Kubernetes **Job** (despite the file being named `templates/deployment.yaml`); `values.yaml` mirrors a subset of the env var config surface.

## Conventions

- Type hints are mandatory and checked under `mypy --strict` (see `[tool.mypy]` in `pyproject.toml`).
- Docstrings follow Google convention (`ruff` `pydocstyle` config).
- Dialect-specific behavior belongs in the `PostgresDatabase`/`SQLServerDatabase` subclasses, not conditionals in `base.py` (`drop_schema` is the existing exception).
- `[tool.uv] exclude-newer = "7 days"` — dependency resolution deliberately ignores releases newer than a week; dependency bumps come through Dependabot PRs.
