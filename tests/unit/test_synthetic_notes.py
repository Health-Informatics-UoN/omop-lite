"""Tests for generating synthetic NOTE / NOTE_NLP data at load time."""

import csv
from pathlib import Path
from typing import Union
from unittest.mock import Mock

import pytest

from omop_lite.db.base import Database
from omop_lite.settings import Settings
from omop_lite.synthetic_notes import generate


class _Db(Database):
    def create_schema(self, schema_name: str) -> None:
        pass

    def _bulk_load(self, table_name: str, file_path: Union[Path, str]) -> None:
        pass


def _db(**overrides: object) -> _Db:
    base: dict[str, object] = {
        "synthetic": True,
        "synthetic_number": 1001,
        "synthetic_notes": True,
    }
    base.update(overrides)
    return _Db(Settings(**base))


@pytest.mark.parametrize(
    "overrides",
    [
        {"synthetic_notes": False},
        {"synthetic": False},
        {"synthetic_number": 100},
        {"omop_version": "omop5_3"},
    ],
)
def test_no_generation_when_not_applicable(tmp_path: Path, overrides: dict[str, object]) -> None:
    assert _db(**overrides)._generate_synthetic_notes(tmp_path) == {}
    assert not any(tmp_path.iterdir())


def test_generated_files_are_loaded(tmp_path: Path) -> None:
    db = _db()
    loaded: dict[str, str] = {}
    db._bulk_load = Mock(side_effect=lambda t, f: loaded.setdefault(t, str(f)))  # type: ignore[method-assign]

    db.load_data()

    assert "note" in loaded and "note_nlp" in loaded
    assert "omop-lite-notes-" in loaded["note"]
    assert Path(loaded["note"]).name == "NOTE.csv"
    # Temporary directory is removed once loading finishes
    assert not Path(loaded["note"]).exists()


@pytest.mark.parametrize("dataset", ["1000", "1001"])
def test_generate_output_matches_note_concepts(tmp_path: Path, dataset: str) -> None:
    """Every note's fixed concept IDs exist in the shipped CONCEPT.csv (FKs)."""
    from importlib.resources import as_file, files

    with as_file(files(f"omop_lite.synthetic.{dataset}")) as src:
        stats = generate(Path(src), tmp_path, seed=42, op_fraction=1.0)
        with open(Path(src) / "CONCEPT.csv", newline="") as f:
            concepts = {r["concept_id"] for r in csv.DictReader(f)}

    assert stats["notes"] > 0 and stats["note_nlp"] > 0
    with open(tmp_path / "NOTE.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == stats["notes"]
    for col in ("note_type_concept_id", "note_class_concept_id",
                "encoding_concept_id", "language_concept_id"):
        assert {r[col] for r in rows} <= concepts, col
