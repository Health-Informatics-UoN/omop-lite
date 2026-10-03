#!/usr/bin/env python3
"""Sync vendored OMOP CDM DDL files from the OHDSI CommonDataModel repo.

omop-lite vendors its DDL (``ddl.sql``, ``constraints.sql``, ``indices.sql``,
``primary_keys.sql``) rather than generating it, because OHDSI's own files
are the source of truth for the CDM. OHDSI doesn't semver those files
independently of a repo release, so each OMOP version below is pinned to a
specific CommonDataModel git tag. Bumping a tag and re-running this script is
the whole update process - the diff it produces is what would otherwise be
silent drift.

Usage:
    uv run python tools/sync_cdm_ddl.py [omop5_3] [omop5_4] [omop5_5]

With no arguments, syncs every version in PINNED_TAGS.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

REPO = "OHDSI/CommonDataModel"

# Each OMOP version is pinned to a specific CommonDataModel release tag, not
# to `main` - bumping one of these is a deliberate, reviewable change rather
# than picking up whatever OHDSI has changed since.
PINNED_TAGS: dict[str, str] = {
    "omop5_3": "v5.3.2",
    "omop5_4": "v5.4.3",
    "omop5_5": "v5.5.0",
}

# Per-(omop_version, our_dialect) tag overrides, for combinations OHDSI added
# to a version's ddl/ folder on `main` after that version's own last tagged
# release - e.g. DuckDB support for 5.3 doesn't exist at tag v5.3.2 (that
# predates DuckDB support entirely), only in later whole-repo snapshots.
TAG_OVERRIDES: dict[tuple[str, str], str] = {
    ("omop5_3", "duckdb"): "v5.4.3",
}

# Our dialect directory name -> OHDSI's dialect directory/file-name segment.
DIALECTS: dict[str, str] = {
    "pg": "postgresql",
    "mssql": "sql_server",
    "duckdb": "duckdb",
}

# Our omop_version name -> OHDSI's ddl/<version> directory segment.
VERSION_NUMBERS: dict[str, str] = {
    "omop5_3": "5.3",
    "omop5_4": "5.4",
    "omop5_5": "5.5",
}

FILE_KINDS = ["ddl", "constraints", "indices", "primary_keys"]

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent / "omop_lite" / "scripts"

# DuckDB cannot add foreign keys to an existing table via
# `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` (see
# https://github.com/duckdb/duckdb/pull/24286), unlike primary keys, which
# can be added after creation. OHDSI's own `duckdb/*_constraints.sql` files
# still contain real FK statements regardless, so this is a structural
# override of what gets written for every duckdb/constraints.sql, not a tag
# pin - omop_lite/db/duckdb.py::DuckDBDatabase.add_constraints documents the
# same limitation and skips FK enforcement for this dialect at runtime.
DUCKDB_CONSTRAINTS_NOOP = """\
--duckdb CDM Foreign Key Constraints for OMOP Common Data Model {version_number}
--
-- Intentionally empty. DuckDB does not support adding foreign keys to an
-- existing table via ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY (unlike
-- PRIMARY KEY, which can be added after creation - see primary_keys.sql).
-- See https://github.com/duckdb/duckdb/pull/24286 for upstream progress.
-- Foreign key enforcement is skipped entirely for this dialect.
"""


def sync_version(omop_version: str, tag: str) -> None:
    """Download all dialect DDL files for one OMOP version at a pinned tag."""
    version_number = VERSION_NUMBERS[omop_version]
    for our_dialect, ohdsi_dialect in DIALECTS.items():
        dialect_tag = TAG_OVERRIDES.get((omop_version, our_dialect), tag)
        for kind in FILE_KINDS:
            dest = SCRIPTS_ROOT / our_dialect / omop_version / f"{kind}.sql"
            dest.parent.mkdir(parents=True, exist_ok=True)

            if our_dialect == "duckdb" and kind == "constraints":
                print(f"(no-op placeholder) -> {dest.relative_to(SCRIPTS_ROOT.parent.parent)}")
                dest.write_text(
                    DUCKDB_CONSTRAINTS_NOOP.format(version_number=version_number)
                )
                continue

            url = (
                f"https://raw.githubusercontent.com/{REPO}/{dialect_tag}/inst/ddl/"
                f"{version_number}/{ohdsi_dialect}/"
                f"OMOPCDM_{ohdsi_dialect}_{version_number}_{kind}.sql"
            )
            print(f"{url} -> {dest.relative_to(SCRIPTS_ROOT.parent.parent)}")
            with urllib.request.urlopen(url) as response:
                dest.write_bytes(response.read())


def main() -> None:
    """Sync the versions named on argv, or all pinned versions by default."""
    versions = sys.argv[1:] or list(PINNED_TAGS)
    for omop_version in versions:
        if omop_version not in PINNED_TAGS:
            raise SystemExit(
                f"Unknown omop version '{omop_version}', expected one of "
                f"{list(PINNED_TAGS)}"
            )
        sync_version(omop_version, PINNED_TAGS[omop_version])


if __name__ == "__main__":
    main()
