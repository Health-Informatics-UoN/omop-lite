#!/usr/bin/env python3
"""
Generate synthetic OMOP CDM v5.4 NOTE and NOTE_NLP tables for the omop-lite
synthetic datasets (Synthea-derived "1000" / "1001" sets, AWS synthea-omop).

Every note is built from the patient's *own* records in the source dataset:
the visit it belongs to, conditions/drugs/procedures/measurements linked to
that visit, allergies, and the patient's prior condition history. NOTE_NLP
rows are emitted for every concept mention inserted into the text, so
`offset`, `lexical_variant` and `snippet` always match `note_text` exactly.

Note structure follows UK NHS conventions:
  * Outpatient note      - PRSB Outpatient Letter Standard (letter to GP, copy to patient)
  * Emergency dept note  - PRSB Emergency Care Discharge Standard
  * Admission note       - UK medical admission clerking (PC / HPC / PMH / DH / SH / FH ...)
  * Discharge summary    - PRSB eDischarge Summary (Transfer of Care, Acute Inpatient Discharge)
  * Radiology report     - RCR Standards for interpretation and reporting of imaging investigations
UK date format (DD-Mon-YYYY), 24-hour times and UK spelling are used throughout.
Concept names are inserted as they appear in the vocabulary (US spellings
from SNOMED / RxNorm / LOINC), so lexical_variant matches the concept name.

Output is deterministic for a given --seed.

All concept IDs the script reads or writes are defined in the CONCEPT
MAPPINGS block below; change mappings there and nowhere else.

Usage:
    python generate_notes.py --source path/to/omop_lite/synthetic/1001 --out out/
    python generate_notes.py --source ... --out ... --install path/to/omop-lite

After generating, any concept in NOTE_CONCEPT_ROWS that is missing from the
--source CONCEPT.csv is appended to it (idempotent; existing rows are never
changed, only reported if they differ). Use --skip-concept-update to leave
CONCEPT.csv untouched.

--install copies NOTE.csv / NOTE_NLP.csv into omop_lite/synthetic/1000 and 1001
and applies the same CONCEPT.csv check to each. It does not touch git.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

# ==========================================================================
# CONCEPT MAPPINGS - every concept ID used by this script is defined here.
# ==========================================================================

# --- Written into NOTE --------------------------------------------------
NOTE_TYPE_EHR = 32817       # note_type_concept_id: EHR
ENCODING_UTF8 = 32678       # encoding_concept_id: UTF-8 (CDM v5.4 ETL conventions)
LANGUAGE_ENGLISH = 4180186  # language_concept_id: English language

# note_class_concept_id per note kind (LOINC). The name is also written to
# note_source_value (max 50 chars).
NOTE_CLASS = {
    "discharge": (3965090, "Discharge summary"),
    "admission": (40770449, "Admission evaluation note"),
    "outpatient": (3030624, "Outpatient note"),
    "radiology": (42528196, "Radiology Technician Note"),
    "emergency": (3029201, "Emergency department Note"),
}

# --- Written into NOTE_NLP ----------------------------------------------
# note_nlp_concept_id / note_nlp_source_concept_id come from the source
# clinical tables. NO_MATCHING_CONCEPT is used when there is no source concept,
# and source rows with this ID are never mentioned in note text.
NO_MATCHING_CONCEPT = 0

# --- Read from the source data ------------------------------------------
# visit_concept_id -> which note kinds are generated
VISIT_IP = 9201  # Inpatient Visit      -> admission clerking + discharge summary
VISIT_OP = 9202  # Outpatient Visit     -> outpatient clinic letter
VISIT_ER = 9203  # Emergency Room Visit -> ED discharge summary

# gender_concept_id -> wording ("man"/"woman", He/She)
GENDER_MALE = 8507
GENDER_FEMALE = 8532

# OBSERVATION rows are picked out by concept *name*, not ID, so they keep
# working across vocabulary versions. Matched case-insensitively.
ALLERGY_NAME_PREFIX = "allergy to"  # -> Allergies sections
SMOKING_NAME_WORDS = ("smokes",)    # -> social history (SH) in clerking

# --- Rows ensured in CONCEPT.csv ----------------------------------------
# omop-lite's trimmed CONCEPT.csv lacks the NOTE concepts above, so these rows
# are appended if their concept_id is missing (FK constraints in
# constraints.sql need them). concept_code values are local placeholders;
# a full Athena vocabulary load replaces them. Columns match CONCEPT.csv.
_VALID = {"valid_start_date": "1970-01-01", "valid_end_date": "2099-12-31", "invalid_reason": ""}
NOTE_CONCEPT_ROWS: list[dict[str, str | int]] = [
    {"concept_id": NOTE_TYPE_EHR, "concept_name": "EHR", "domain_id": "Type Concept",
     "vocabulary_id": "Type Concept", "concept_class_id": "Type Concept", "standard_concept": "S",
     "concept_code": f"OMOP{NOTE_TYPE_EHR}", **_VALID},
    {"concept_id": ENCODING_UTF8, "concept_name": "UTF-8", "domain_id": "Metadata",
     "vocabulary_id": "None", "concept_class_id": "Undefined", "standard_concept": "",
     "concept_code": f"OMOP{ENCODING_UTF8}", **_VALID},
    {"concept_id": LANGUAGE_ENGLISH, "concept_name": "English language", "domain_id": "Language",
     "vocabulary_id": "SNOMED", "concept_class_id": "Qualifier Value", "standard_concept": "S",
     "concept_code": f"OMOP{LANGUAGE_ENGLISH}", **_VALID},
] + [
    {"concept_id": cid, "concept_name": name, "domain_id": "Note", "vocabulary_id": "LOINC",
     "concept_class_id": "Clinical Observation", "standard_concept": "S", "concept_code": f"OMOP{cid}", **_VALID}
    for cid, name in NOTE_CLASS.values()
]

# ==========================================================================
# END OF CONCEPT MAPPINGS
# ==========================================================================

NLP_SYSTEM = "omop-lite-synthetic-notes v0.2"

# Stems, so "fluoroscop" matches "Fluoroscopy guided ..." and "mammogra" matches "Mammography";
# word boundaries stop "ct" matching inside e.g. "Direct current cardioversion".
IMAGING_RE = re.compile(r"x-ray|radiograph|computed tomography|\bct\b|\bmri\b|magnetic resonance|"
                        r"ultraso|mammogra|fluoroscop|echocardiograph|imaging", re.I)
INTERVENTIONAL_WORDS = ("guided", "percutaneous", "thrombectomy", "biopsy", "insertion", "drainage",
                        "angioplasty", "embolization")
SURGICAL_WORDS = ("ectomy", "otomy", "plasty", "repair", "replacement", "excision", "amputation",
                  "insertion", "reduction")


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_date(s: str) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def ukdate(d: date) -> str:
    return d.strftime("%d-%b-%Y")


@dataclass
class Mention:
    concept_id: int
    source_concept_id: int | None
    name: str


@dataclass
class VisitData:
    conditions: list[tuple[Mention, str]] = field(default_factory=list)  # (mention, condition_occurrence_id)
    drugs: list[Mention] = field(default_factory=list)
    procedures: list[Mention] = field(default_factory=list)
    measurements: list[tuple[Mention, str]] = field(default_factory=list)  # (mention, value)


class Source:
    def __init__(self, src: Path):
        self.concepts = {r["concept_id"]: r for r in read_csv(src / "CONCEPT.csv")}
        self.persons = {r["person_id"]: r for r in read_csv(src / "PERSON.csv")}
        self.visits = read_csv(src / "VISIT_OCCURRENCE.csv")
        self.by_visit: dict[str, VisitData] = defaultdict(VisitData)
        # person -> list of (start_date, mention) for history
        self.history: dict[str, list[tuple[date, Mention]]] = defaultdict(list)
        # person -> list of (date, mention) for allergies / smoking (OBSERVATION)
        self.allergies: dict[str, list[tuple[date, Mention]]] = defaultdict(list)
        self.smoking: dict[str, list[tuple[date, Mention]]] = defaultdict(list)
        # person -> list of (date, procedure mention) for imaging comparison
        self.imaging: dict[str, list[tuple[date, Mention]]] = defaultdict(list)
        # person -> sorted visits (for first attendance / ED->admission links)
        self.person_visits: dict[str, list[dict[str, str]]] = defaultdict(list)
        for v in self.visits:
            if parse_date(v["visit_start_date"]):
                self.person_visits[v["person_id"]].append(v)
        for vs in self.person_visits.values():
            vs.sort(key=lambda v: (v["visit_start_date"], int(v["visit_occurrence_id"])))

        for r in read_csv(src / "CONDITION_OCCURRENCE.csv"):
            m = self._mention(r["condition_concept_id"], r["condition_source_concept_id"], "Condition")
            if not m:
                continue
            self.by_visit[r["visit_occurrence_id"]].conditions.append((m, r["condition_occurrence_id"]))
            d = parse_date(r["condition_start_date"])
            if d:
                self.history[r["person_id"]].append((d, m))

        for r in read_csv(src / "DRUG_EXPOSURE.csv"):
            m = self._mention(r["drug_concept_id"], None, "Drug")
            if m:
                self.by_visit[r["visit_occurrence_id"]].drugs.append(m)

        for r in read_csv(src / "PROCEDURE_OCCURRENCE.csv"):
            m = self._mention(r["procedure_concept_id"], r["procedure_source_concept_id"], "Procedure")
            if m:
                self.by_visit[r["visit_occurrence_id"]].procedures.append(m)
                d = parse_date(r["procedure_date"])
                if d and is_imaging(m.name):
                    self.imaging[r["person_id"]].append((d, m))

        for r in read_csv(src / "MEASUREMENT.csv"):
            m = self._mention(r["measurement_concept_id"], None, "Measurement")
            if m and r["value_as_number"]:
                self.by_visit[r["visit_occurrence_id"]].measurements.append((m, r["value_as_number"]))

        for r in read_csv(src / "OBSERVATION.csv"):
            m = self._mention(r["observation_concept_id"], r["observation_source_concept_id"], "Observation")
            d = parse_date(r["observation_date"])
            if not m or not d:
                continue
            if m.name.lower().startswith(ALLERGY_NAME_PREFIX):
                self.allergies[r["person_id"]].append((d, m))
            elif any(w in m.name.lower() for w in SMOKING_NAME_WORDS):
                self.smoking[r["person_id"]].append((d, m))

        # Pool for negated / family-history / rule-out mentions: the most
        # common non-injury conditions in this dataset.
        freq: dict[int, int] = defaultdict(int)
        names: dict[int, str] = {}
        for hist in self.history.values():
            for _, m in hist:
                freq[m.concept_id] += 1
                names[m.concept_id] = m.name
        skip = ("fracture", "laceration", "injury", "sprain", "rupture", "burn", "pregnan",
                "bite", "wound", "concussion", "contusion", "dislocation", "abrasion", "finding")
        ranked = sorted((c for c in freq if not any(w in names[c].lower() for w in skip)),
                        key=lambda c: (-freq[c], c))
        self.condition_pool = [(c, names[c]) for c in ranked[:40]]

    def _mention(self, cid: str, scid: str | None, domain: str) -> Mention | None:
        c = self.concepts.get(cid)
        if not c or int(cid) == NO_MATCHING_CONCEPT or c["domain_id"] != domain:
            return None
        src = int(scid) if scid and int(scid) != NO_MATCHING_CONCEPT and scid in self.concepts else None
        return Mention(int(cid), src, c["concept_name"])

    def known_allergies(self, person_id: str, on: date) -> list[Mention]:
        return dedupe([m for d, m in sorted(self.allergies.get(person_id, []), key=lambda x: x[0]) if d <= on])

    def smoker(self, person_id: str, on: date) -> Mention | None:
        prior = [m for d, m in self.smoking.get(person_id, []) if d <= on]
        return prior[-1] if prior else None

    def prior_imaging(self, person_id: str, proc: Mention, before: date) -> date | None:
        prior = [d for d, m in self.imaging.get(person_id, []) if m.concept_id == proc.concept_id and d < before]
        return max(prior) if prior else None

    def adjacent_visit(self, v: dict[str, str], concept: int, days: tuple[int, int]) -> dict[str, str] | None:
        """A visit of `concept` for the same person starting days[0]..days[1] after v starts."""
        start = parse_date(v["visit_start_date"])
        for o in self.person_visits.get(v["person_id"], []):
            if o is v or visit_kind(o) != concept:
                continue
            delta = (parse_date(o["visit_start_date"]) - start).days
            if days[0] <= delta <= days[1]:
                return o
        return None

    def is_first_attendance(self, v: dict[str, str]) -> bool:
        for o in self.person_visits.get(v["person_id"], []):
            if visit_kind(o) == VISIT_OP:
                return o is v
        return False


def visit_kind(v: dict[str, str]) -> int | None:
    try:
        return int(v["visit_concept_id"])
    except (KeyError, ValueError):
        return None


def is_imaging(name: str) -> bool:
    return bool(IMAGING_RE.search(name))


def modality(name: str) -> str:
    n = name.lower()
    if "computed tomography" in n or re.search(r"\bct\b", n):
        return "CT"
    if "magnetic resonance" in n or re.search(r"\bmri\b", n):
        return "MR"
    if "mammogra" in n:
        return "MG"
    if "fluoroscop" in n:
        return "FL"
    if "ultraso" in n or "echocardiograph" in n:
        return "US"
    return "XR"


# --------------------------------------------------------------------------
# Note builder: appends text and records exact NLP spans
# --------------------------------------------------------------------------
@dataclass
class Span:
    start: int
    text: str
    concept_id: int
    source_concept_id: int | None
    exists: str  # Y / N
    temporal: str  # present / past
    modifiers: str


def modifiers(negated=False, subject="patient", conditional=False, rule_out=False,
              uncertain="false", history=False, value: str | None = None) -> str:
    # Only non-default modifiers are listed; an empty string means an
    # affirmed, current, patient-level mention (term_exists = Y).
    parts = []
    if negated:
        parts.append("negated=true")
    if subject != "patient":
        parts.append(f"subject={subject}")
    if conditional:
        parts.append("conditional=true")
    if rule_out:
        parts.append("rule_out=true")
    if uncertain != "false":
        parts.append(f"uncertain={uncertain}")
    if history:
        parts.append("history=true")
    if value is not None:
        parts.append(f"value={value}")
    return ";".join(parts)


class NoteBuilder:
    def __init__(self) -> None:
        self.buf: list[str] = []
        self.pos = 0
        self.spans: list[Span] = []

    def add(self, s: str) -> None:
        self.buf.append(s)
        self.pos += len(s)

    def line(self, s: str = "") -> None:
        self.add(s + "\n")

    def section(self, title: str) -> None:
        if self.pos:
            self.add("\n")
        self.line(title.upper() + ":")

    def field(self, label: str, value: str) -> None:
        self.line(f"{label}: {value}")

    def term(self, m: Mention, *, exists="Y", temporal="present", mods: str | None = None,
             text: str | None = None) -> None:
        t = text if text is not None else m.name
        self.spans.append(Span(self.pos, t, m.concept_id, m.source_concept_id, exists, temporal,
                               mods or modifiers()))
        self.add(t)

    def terms_inline(self, ms: list[Mention], lower: bool = True, **kw) -> None:
        for i, m in enumerate(ms):
            if i:
                self.add(" and " if i == len(ms) - 1 else ", ")
            self.term(m, text=lc_first(m.name) if lower else m.name, **kw)

    def text(self) -> str:
        return "".join(self.buf).rstrip() + "\n"


def lc_first(s: str) -> str:
    return s[0].lower() + s[1:] if s and not s[:2].isupper() else s


def age_at(person: dict[str, str], on: date) -> int | None:
    try:
        y, mo, d = int(person["year_of_birth"]), int(person["month_of_birth"] or 1), int(person["day_of_birth"] or 1)
    except ValueError:
        return None
    return on.year - y - ((on.month, on.day) < (mo, d))


@dataclass
class Demo:
    age: int | None
    noun: str  # "62-year-old man"
    short: str  # "62M"
    pron: str  # He / She / They
    poss: str  # his / her / their
    child: bool


def demographic(person: dict[str, str], on: date) -> Demo:
    age = age_at(person, on)
    try:
        gid = int(person["gender_concept_id"])
    except (KeyError, ValueError):
        gid = None
    g = {GENDER_MALE: "M", GENDER_FEMALE: "F"}.get(gid, "")
    child = age is not None and age < 16
    word = {("M", False): "man", ("F", False): "woman", ("M", True): "boy", ("F", True): "girl"}.get((g, child), "patient")
    pron, poss = {"M": ("He", "his"), "F": ("She", "her")}.get(g, ("They", "their"))
    if age is None:
        return Demo(None, word, g or "?", pron, poss, False)
    if age < 1:
        noun = f"infant {word}" if word != "patient" else "infant"
        short = f"<1y {g}"
    else:
        noun = f"{age}-year-old {word}"
        short = f"{age}{g}"
    return Demo(age, noun, short, pron, poss, child)


def dedupe(ms: list[Mention]) -> list[Mention]:
    seen, out = set(), []
    for m in ms:
        if m.concept_id not in seen:
            seen.add(m.concept_id)
            out.append(m)
    return out


@dataclass
class Ctx:
    """Everything a note template needs about one visit."""
    src: Source
    v: dict[str, str]
    vd: VisitData
    rng: random.Random
    start: date
    end: date
    demo: Demo
    conds: list[Mention]
    drugs: list[Mention]
    procs: list[Mention]
    patient_cids: set[int]
    seed: int
    ed_visit: dict[str, str] | None  # for admissions: the ED attendance that led to it

    @classmethod
    def make(cls, src: Source, v: dict[str, str], vd: VisitData, rng: random.Random, seed: int) -> "Ctx":
        start = parse_date(v["visit_start_date"])
        end = parse_date(v["visit_end_date"]) or start
        if end < start:
            end = start
        conds = [m for m, _ in vd.conditions]
        procs = list(vd.procedures)
        ed = src.adjacent_visit(v, VISIT_ER, (-1, 0)) if visit_kind(v) == VISIT_IP else None
        if ed:
            # The diagnosis is usually recorded on the ED attendance; carry it into the admission.
            edd = src.by_visit.get(ed["visit_occurrence_id"], VisitData())
            conds = [m for m, _ in edd.conditions] + conds
            procs = procs + list(edd.procedures)
        return cls(src, v, vd, rng, start, end, demographic(src.persons[v["person_id"]], start),
                   dedupe(conds), dedupe(vd.drugs), dedupe(procs),
                   {m.concept_id for _, m in src.history.get(v["person_id"], [])}, seed, ed)

    def pool(self, exclude=()) -> list[tuple[int, str]]:
        return [c for c in self.src.condition_pool if c[0] not in self.patient_cids
                and not any(w in c[1].lower() for w in exclude)]


def clock(rng: random.Random, lo: int = 8, hi: int = 18) -> tuple[int, int]:
    return rng.randint(lo, hi), rng.choice(range(0, 60, 5))


def ed_times(seed: int, ed_visit: dict[str, str]) -> tuple[datetime, datetime]:
    """Arrival/departure for an ED attendance; own RNG so admissions can line up with it."""
    r = random.Random(f"{seed}:ed:{ed_visit['visit_occurrence_id']}")
    d = parse_date(ed_visit["visit_start_date"])
    arrive = datetime(d.year, d.month, d.day, r.randint(0, 21), r.choice(range(0, 60, 5)))
    depart = arrive + timedelta(minutes=r.randint(90, 330))
    # The source ER visits start and end on the same date; keep the note inside the visit.
    return arrive, min(depart, datetime(d.year, d.month, d.day, 23, 55))


# --------------------------------------------------------------------------
# Shared sections
# --------------------------------------------------------------------------
def pmh_items(c: Ctx, limit: int = 6) -> list[tuple[date, Mention]]:
    hist = {}
    current = {m.concept_id for m in c.conds}
    for d, m in sorted(c.src.history.get(c.v["person_id"], []), key=lambda x: x[0]):
        if d < c.start and m.concept_id not in current and m.concept_id not in hist:
            hist[m.concept_id] = (d, m)
    return list(hist.values())[-limit:]


def add_pmh(nb: NoteBuilder, c: Ctx, title: str = "Past medical history") -> None:
    nb.section(title)
    items = pmh_items(c)
    if not items:
        nb.line("Nil of note.")
        return
    for d, m in items:
        nb.add("- ")
        nb.term(m, temporal="past", mods=modifiers(history=True))
        nb.line(f" ({d.year})")


def add_negations(nb: NoteBuilder, c: Ctx, style: str = "prose") -> None:
    pool = c.pool()
    if not pool:
        return
    picks = c.rng.sample(pool, k=min(len(pool), c.rng.choice([1, 2])))
    for cid, name in picks:
        m = Mention(cid, cid, name)
        if style == "terse":
            lead = c.rng.choice(["No hx of ", "No evidence of ", "Nil to suggest "])
        else:
            lead = c.rng.choice([f"{c.demo.pron} denies any history of ", "There is no history of ",
                                 "No features to suggest "])
        nb.add(lead)
        nb.term(m, exists="N", mods=modifiers(negated=True), text=lc_first(name))
        nb.add(". ")


def add_family_history(nb: NoteBuilder, c: Ctx, title: str = "Family history") -> None:
    nb.section(title)
    if c.rng.random() < 0.45 or not c.src.condition_pool:
        nb.line("Nil of note.")
        return
    cid, name = c.rng.choice(c.src.condition_pool)
    rel = c.rng.choice(["Mother", "Father", "Sister", "Brother", "Maternal grandmother", "Paternal grandfather"])
    nb.add(f"{rel}: ")
    nb.term(Mention(cid, cid, name), exists="N", temporal="past",
            mods=modifiers(subject="family_member", history=True), text=lc_first(name))
    nb.line(".")


def add_allergies(nb: NoteBuilder, c: Ctx, title: str = "Allergies and adverse reactions") -> None:
    nb.section(title)
    al = c.src.known_allergies(c.v["person_id"], c.start)
    if not al:
        nb.line("No known drug allergies.")
        return
    for m in al[:6]:
        nb.add("- ")
        nb.term(m)
        nb.line()


def add_meds(nb: NoteBuilder, c: Ctx, title: str, status_choices: list[str], empty: str) -> None:
    nb.section(title)
    if not c.drugs:
        nb.line(empty)
        return
    for m in c.drugs[:8]:
        nb.add("- ")
        nb.term(m)
        nb.line(" - " + c.rng.choice(status_choices))


def add_results(nb: NoteBuilder, c: Ctx, title: str = "Investigation results", lead: str | None = None) -> None:
    seen, items = set(), []
    for m, _ in c.vd.measurements:
        if m.concept_id not in seen:
            seen.add(m.concept_id)
            items.append(m)
    if not items:
        return
    # value_as_number in the Synthea-OMOP source is a placeholder 0-10
    # integer, so values are deliberately not written into the narrative.
    nb.section(title)
    nb.line(lead or "Results reviewed (see results system for values):")
    for m in items[:8]:
        nb.add("- ")
        nb.term(m)
        nb.line()


def add_procedures(nb: NoteBuilder, c: Ctx, title: str = "Procedures", limit: int = 5) -> None:
    if not c.procs:
        return
    nb.section(title)
    for m in c.procs[:limit]:
        nb.add("- ")
        nb.term(m)
        nb.line()


def add_rule_out(nb: NoteBuilder, c: Ctx, lead: str, tail: str, p: float = 0.2) -> None:
    if c.rng.random() >= p:
        return
    pool = c.pool(exclude=("arrest", "history of", "normal", "deficit", "obesity"))
    if not pool:
        return
    cid, name = c.rng.choice(pool)
    nb.add(lead)
    nb.term(Mention(cid, cid, name), exists="N", mods=modifiers(rule_out=True, uncertain="moderate"),
            text=lc_first(name))
    nb.line(tail)


def add_distribution(nb: NoteBuilder, c: Ctx) -> None:
    nb.section("Distribution list")
    nb.line("- GP practice")
    nb.line("- Parent/carer (copy)" if c.demo.child else "- Patient (copy)")


# --------------------------------------------------------------------------
# Outpatient letter (PRSB Outpatient Letter Standard)
# --------------------------------------------------------------------------
def specialty_for(c: Ctx) -> str:
    if c.demo.child:
        return "Paediatrics"
    names = " ".join(m.name.lower() for m in c.conds + c.procs)
    for words, spec in [
        (("diabetes", "prediabetes", "hyperglyc"), "Diabetes and Endocrinology"),
        (("heart", "cardiac", "hypertension", "atrial", "coronary"), "Cardiology"),
        (("asthma", "pulmonary", "bronch", "lung", "respiratory"), "Respiratory Medicine"),
        (("kidney", "renal"), "Renal Medicine"),
        (("pregnan", "fetal", "uterine", "contracept", "miscarriage", "obstetric"), "Obstetrics and Gynaecology"),
        (("fracture", "sprain", "osteoarthritis", "joint", "knee", "hip"), "Trauma and Orthopaedics"),
        (("depress", "anxiety", "stress", "alcohol", "drug abuse"), "Psychiatry"),
        (("sinusitis", "pharyngitis", "otitis", "throat", "tonsil"), "Ear, Nose and Throat"),
        (("colon", "bowel", "gastr", "appendic", "hepat"), "Gastroenterology"),
    ]:
        if any(w in names for w in words):
            return spec
    return "General Medicine"


def build_outpatient(c: Ctx):
    rng, d = c.rng, c.demo
    spec = specialty_for(c)
    first = c.src.is_first_attendance(c.v)
    nb = NoteBuilder()
    nb.line(f"{spec.upper()} OUTPATIENT CLINIC LETTER")
    nb.field("Clinic date", ukdate(c.start))
    nb.field("Contact type", "First attendance" if first else "Follow-up attendance")
    nb.field("Consultation method", rng.choices(["Face to face", "Telephone", "Video"], [8, 2, 1])[0])
    nb.field("Patient", d.noun)
    nb.line()
    nb.line("Dear Colleague,")

    nb.section("Diagnoses")
    if c.conds:
        for i, m in enumerate(c.conds[:5], 1):
            nb.add(f"{i}. ")
            nb.term(m)
            nb.line()
    else:
        nb.line("No new diagnosis.")

    nb.line()
    if first:
        nb.add(f"Thank you for referring this {d.noun}, whom I saw in the {spec.lower()} clinic today. ")
    else:
        nb.add(f"I reviewed this {d.noun} in the {spec.lower()} clinic today. ")
    if d.child:
        nb.add(f"{d.pron} attended with a parent. ")
    nb.line()

    nb.section("History")
    if c.conds:
        nb.add(f"{d.pron} presented with ")
        nb.terms_inline(c.conds[:3])
        nb.add(". ")
        nb.add(rng.choice([
            "Symptoms started a few days ago and have gradually worsened. ",
            "Onset was recent. ",
            f"{d.pron} reports the symptoms have been intermittent. ",
            "",
        ]))
    else:
        nb.add(rng.choice([f"{d.pron} attended for a routine review. ",
                           f"{d.pron} attended for planned review and is generally well. "]))
    add_negations(nb, c)
    nb.line()

    add_pmh(nb, c)
    add_allergies(nb, c)
    if not d.child and rng.random() < 0.5:
        add_family_history(nb, c)
    add_results(nb, c)
    add_procedures(nb, c, "Procedures", limit=4)

    nb.section("Clinical summary")
    if c.conds:
        nb.add("Clinical findings are in keeping with ")
        nb.term(c.conds[0], text=lc_first(c.conds[0].name))
        nb.line(". " + rng.choice([
            "I have explained the diagnosis and we agreed a management plan together.",
            "We discussed the diagnosis and treatment options and agreed a plan.",
            f"{d.pron} is happy with the plan outlined below.",
        ]))
    else:
        nb.line(rng.choice(["No acute concerns were identified today.",
                            "Review was satisfactory with no new concerns."]))

    add_meds(nb, c, "Medications and medical devices",
             ["started today", "continue", "continue, no change", "new - please add to repeat prescription"],
             "No changes.")

    nb.section("Information and advice given")
    nb.line(rng.choice([
        "Diagnosis and management plan discussed. Written information provided.",
        "Plan discussed and agreed. Advised to contact the clinic if symptoms worsen.",
        "Lifestyle advice given. Advised to see GP if any new symptoms develop.",
    ]))

    nb.section("Plan and requested actions")
    nb.line("Actions for GP:")
    gp_actions = []
    if c.drugs:
        gp_actions.append("- Please continue the medications listed above.")
    if c.conds and rng.random() < 0.5:
        gp_actions.append(f"- Please review in {rng.choice(['2', '4', '6'])} weeks.")
    for a in gp_actions or ["- No GP action required."]:
        nb.line(a)
    add_rule_out(nb, c, "- I have requested further tests to exclude ", ". I will write with the results.")
    nb.line("Actions for patient:" if not d.child else "Actions for parent/carer:")
    nb.line(rng.choice(["- Take medications as prescribed." if c.drugs else "- No specific actions.",
                        "- Contact the clinic or GP if symptoms worsen."]))
    nb.line(rng.choice([
        "Follow-up: Discharged back to the care of the GP.",
        f"Follow-up: Clinic review in {rng.choice(['3', '6', '12'])} months.",
        "Follow-up: Another appointment will be made at a later date.",
    ]))
    nb.line()
    nb.line("Yours sincerely,")
    nb.line()
    nb.line(rng.choice(["Consultant", "Specialty Registrar", "Clinical Nurse Specialist"]) + f", {spec}")
    add_distribution(nb, c)
    h, mi = clock(rng)
    return f"{spec} Outpatient Letter", nb, c.start, (h, mi)


# --------------------------------------------------------------------------
# Emergency department (PRSB Emergency Care Discharge Standard)
# --------------------------------------------------------------------------
SEVERE_WORDS = ("cardiac arrest", "myocardial infarction", "cerebrovascular accident", "sepsis",
                "septic shock", "stroke")


def build_emergency(c: Ctx):
    rng, d = c.rng, c.demo
    admitted = c.src.adjacent_visit(c.v, VISIT_IP, (0, 1))
    severe = any(any(w in m.name.lower() for w in SEVERE_WORDS) for m in c.conds[:2])
    arrive, depart = ed_times(c.seed, c.v)
    nb = NoteBuilder()
    nb.line("EMERGENCY DEPARTMENT DISCHARGE SUMMARY")
    nb.field("Arrival", f"{ukdate(arrive.date())} {arrive:%H:%M}")
    nb.field("Patient", d.noun)

    nb.section("Referrer details")
    nb.line(rng.choices(["Self-referral", "Self-referral via NHS 111", "Ambulance (999)", "GP referral"],
                        [4, 2, 3, 1])[0])

    nb.section("Presenting complaints or issues")
    if c.conds:
        nb.term(c.conds[0])
        nb.line()
    else:
        nb.line("Unwell, for assessment.")

    nb.section("Clinical narrative")
    nb.add(f"{d.short}. ")
    if c.conds:
        nb.add("Presents with ")
        nb.terms_inline(c.conds[:2])
        nb.add(". ")
    add_negations(nb, c, style="terse")
    if severe:
        nb.add(rng.choice(["Managed in resus. ", "Seen in resus, senior review. "]))
    else:
        nb.add(rng.choice(["O/E alert, obs stable. ", "O/E comfortable at rest, NEWS2 0. ",
                           "O/E GCS 15, obs within normal limits. "]))
    if c.procs:
        nb.add("Ix: ")
        nb.terms_inline(c.procs[:2], lower=False)
        nb.add(". ")
    nb.line()

    nb.section("Diagnoses")
    if c.conds:
        for i, m in enumerate(c.conds[:4], 1):
            nb.add(f"{i}. ")
            if i == 1 and rng.random() < 0.15:
                nb.add("Suspected ")
                nb.term(m, mods=modifiers(uncertain="moderate"), text=lc_first(m.name))
            else:
                nb.term(m)
            nb.line()
    else:
        nb.line("No definitive diagnosis made.")

    add_procedures(nb, c, limit=4)
    add_results(nb, c)
    add_meds(nb, c, "Medications and medical devices",
             ["started", "given in department", "continue"], "No changes.")
    add_allergies(nb, c)

    nb.section("Plan and requested actions")
    if admitted:
        nb.line("Referred to the medical team for admission.")
    elif severe:
        nb.line("Transferred to specialist centre for ongoing care.")
    else:
        nb.line("Actions for GP: " + rng.choice([
            "No GP action required.", "Please review in 1 week.",
            "Please review if symptoms persist."]))
        nb.line("Actions for patient: " + rng.choice([
            "Complete course of medication." if c.drugs else "Rest and simple analgesia as required.",
            "See GP if not improving within 1 week."]))
    add_rule_out(nb, c, "Further investigation to exclude ", " - for GP follow-up.", p=0.1)

    nb.section("Information and advice given")
    nb.line(rng.choice([
        "Safety-netting advice given: return to ED or call NHS 111 if symptoms worsen.",
        "Verbal and written advice given. Advised to call 999 if any red-flag symptoms.",
    ]))

    nb.section("Discharge details")
    nb.field("Discharged", f"{ukdate(depart.date())} {depart:%H:%M}")
    if admitted:
        nb.field("Status", "Admitted")
        nb.field("Destination", "Admitted to hospital ward")
    elif severe:
        # No inpatient visit follows in the source data, so the patient leaves this provider.
        nb.field("Status", "Transferred")
        nb.field("Destination", "Transferred to another hospital")
    else:
        nb.field("Status", "Treatment complete")
        nb.field("Destination", "Discharged home - follow-up by GP if required")

    nb.section("Person completing record")
    nb.line(rng.choice(["Emergency Medicine Specialty Registrar", "Emergency Medicine Consultant",
                        "Advanced Clinical Practitioner, Emergency Department", "Foundation Year 2 doctor, ED"]))
    return "Emergency Department Discharge Summary", nb, depart.date(), (depart.hour, depart.minute)


# --------------------------------------------------------------------------
# Admission clerking (UK medical clerking)
# --------------------------------------------------------------------------
def admission_route(c: Ctx) -> str:
    if c.ed_visit:
        return "Emergency - via Emergency Department"
    if c.conds:
        return "Emergency - GP referral"
    return "Elective - waiting list"


def admitting_specialty(c: Ctx) -> str:
    if c.demo.child:
        return "Paediatrics"
    if any(any(w in m.name.lower() for w in SURGICAL_WORDS) for m in c.procs):
        return "General Surgery"
    cond_names = " ".join(m.name.lower() for m in c.conds)
    if any(w in cond_names for w in ("appendicitis", "cholecystitis", "bowel obstruction", "hernia")):
        return "General Surgery"
    if "fracture" in cond_names:
        return "Trauma and Orthopaedics"
    return "Acute Medicine"


def build_admission(c: Ctx):
    rng, d = c.rng, c.demo
    route = admission_route(c)
    spec = admitting_specialty(c)
    nb = NoteBuilder()
    nb.line("ADMISSION CLERKING")
    nb.field("Date of admission", ukdate(c.start))
    nb.field("Admission method", route)
    nb.field("Specialty", spec)
    nb.field("Patient", d.noun)

    nb.section("PC")
    if c.conds:
        nb.term(c.conds[0])
        nb.line()
    elif c.procs:
        nb.add("Elective admission for ")
        nb.term(c.procs[0], text=lc_first(c.procs[0].name))
        nb.line()
    else:
        nb.line("Admitted for observation.")

    nb.section("HPC")
    nb.add(f"{d.short}. ")
    if c.conds:
        nb.add(rng.choice(["Presents with ", "Admitted with "]))
        nb.terms_inline(c.conds[:3])
        nb.add(". ")
        nb.add(rng.choice(["Symptoms worsening over 2-3 days. ", "Acute onset today. ",
                           "Gradual deterioration over the past week. "]))
    elif c.ed_visit:
        nb.add("Referred from ED for observation. ")
    else:
        nb.add("Planned admission. Currently well. ")
    add_negations(nb, c, style="terse")
    nb.line()

    add_pmh(nb, c, "PMH")
    nb.section("DH")
    if c.drugs:
        for m in c.drugs[:8]:
            nb.add("- ")
            nb.term(m)
            nb.line()
    else:
        nb.line("Nil regular.")
    add_allergies(nb, c, "Allergies")
    add_family_history(nb, c, "FH")
    nb.section("SH")
    sm = c.src.smoker(c.v["person_id"], c.start)
    if sm:
        nb.term(sm)
        nb.line(".")
    else:
        nb.line("Smoking status not documented. Independent with activities of daily living."
                if not d.child else "Lives with parents.")

    nb.section("O/E")
    nb.line(rng.choice(["Alert and orientated. Observations stable. CVS, RS and abdomen unremarkable.",
                        "Comfortable at rest. HS I+II+0. Chest clear. Abdomen soft, non-tender.",
                        "GCS 15. Observations within normal limits. No focal neurology."]))
    add_results(nb, c, "Investigations", "Requested/reviewed on admission:")

    nb.section("Impression")
    if c.conds:
        for i, m in enumerate(c.conds[:4], 1):
            nb.add(f"{i}. ")
            nb.term(m)
            nb.line()
    else:
        nb.line("Well patient admitted for planned procedure." if c.procs else "No acute diagnosis.")

    nb.section("Plan")
    n = 0
    for m in c.procs[:3]:
        n += 1
        nb.add(f"{n}. ")
        nb.term(m)
        nb.line()
    for line in [rng.choice(["Bloods and observations", "Routine bloods, VTE assessment"]),
                 "Review on post-take ward round"]:
        n += 1
        nb.line(f"{n}. {line}")
    add_rule_out(nb, c, f"{n + 1}. Further investigation to exclude ", "")
    nb.line()
    nb.line("Clerked by: " + rng.choice(["Foundation Year 1 doctor", "Core Medical Trainee",
                                         "Specialty Registrar"]) + f", {spec}")
    if c.ed_visit:
        # Clerked on the ward after leaving ED
        t = ed_times(c.seed, c.ed_visit)[1] + timedelta(minutes=rng.randint(45, 180))
        t = max(t, datetime(c.start.year, c.start.month, c.start.day, 0, 5) + timedelta(minutes=rng.randint(0, 90)))
        t = min(t, datetime(c.end.year, c.end.month, c.end.day, 23, 55))
        return "Admission Clerking", nb, t.date(), (t.hour, t.minute)
    h, mi = clock(rng, 0, 23)
    return "Admission Clerking", nb, c.start, (h, mi)


# --------------------------------------------------------------------------
# Discharge summary (PRSB eDischarge Summary)
# --------------------------------------------------------------------------
def build_discharge(c: Ctx):
    rng, d = c.rng, c.demo
    route = admission_route(c)
    spec = admitting_specialty(c)
    nb = NoteBuilder()
    nb.line("DISCHARGE SUMMARY")
    nb.field("Patient", d.noun)

    nb.section("Admission details")
    nb.field("Date of admission", ukdate(c.start))
    nb.field("Admission method", route)
    nb.field("Source of admission", "Usual place of residence")
    nb.add("Reason for admission: ")
    if c.conds:
        nb.term(c.conds[0])
    elif c.procs:
        nb.term(c.procs[0])
    else:
        nb.add("Observation")
    nb.line()

    nb.section("Discharge details")
    nb.field("Date of discharge", ukdate(c.end))
    nb.field("Discharging specialty", spec)
    nb.field("Discharge method", "Patient discharged on clinical advice or with clinical consent")
    nb.field("Discharge destination", "Usual place of residence")

    nb.section("Diagnoses")
    if c.conds:
        nb.add("Primary diagnosis: ")
        nb.term(c.conds[0])
        nb.line()
        if c.conds[1:]:
            nb.line("Secondary diagnoses:")
            for m in c.conds[1:6]:
                nb.add("- ")
                nb.term(m)
                nb.line()
    else:
        nb.line("No definitive diagnosis.")
    comorb = pmh_items(c, limit=4)
    if comorb:
        nb.line("Comorbidities:")
        for _, m in comorb:
            nb.add("- ")
            nb.term(m, temporal="past", mods=modifiers(history=True))
            nb.line()

    nb.section("Clinical summary")
    nb.add(f"This {d.noun} was admitted on {ukdate(c.start)}")
    if c.conds:
        nb.add(" with ")
        nb.term(c.conds[0], text=lc_first(c.conds[0].name))
    elif c.procs:
        nb.add(" for ")
        nb.term(c.procs[0], text=lc_first(c.procs[0].name))
    nb.add(". ")
    if c.procs[1 if not c.conds else 0:]:
        nb.add(f"During the admission {d.pron.lower()} underwent ")
        nb.terms_inline(c.procs[1 if not c.conds else 0:][:3])
        nb.add(". ")
    nb.add(rng.choice([
        f"{d.pron} responded well to treatment and improved clinically. ",
        f"{d.pron} remained haemodynamically stable throughout the admission. ",
        "The admission was uncomplicated. ",
    ]))
    days = (c.end - c.start).days
    nb.line(f"Length of stay {days} day{'s' if days != 1 else ''}. "
            f"Medically fit for discharge on {ukdate(c.end)}.")

    add_procedures(nb, c)
    add_results(nb, c)
    add_meds(nb, c, "Medications and medical devices",
             ["started during admission", "continue, no change", "dose changed - see GP actions",
              "continue"], "No changes to medication.")
    add_allergies(nb, c)

    nb.section("Information and advice given")
    nb.line(rng.choice([
        "Diagnosis and treatment explained to patient. Advised to seek medical advice if symptoms recur.",
        "Discharge plan discussed and agreed with patient. Written information given.",
    ]))

    nb.section("Plan and requested actions")
    nb.line("Actions for GP:")
    nb.line(rng.choice(["- Please review in 1-2 weeks.", "- Please repeat bloods in 2 weeks.",
                        "- No GP action required."]))
    if c.drugs:
        nb.line("- Please update repeat prescription with the medications above.")
    add_rule_out(nb, c, "- Outpatient investigation to exclude ", " has been requested.", p=0.15)
    nb.line("Actions for patient:")
    nb.line(rng.choice(["- Attend follow-up appointment as booked.",
                        "- Take medications as prescribed.",
                        "- See GP if symptoms return."]))

    nb.section("Person completing record")
    nb.line(rng.choice(["Foundation Year 1 doctor", "Specialty Registrar", "Consultant"]) + f", {spec}")
    nb.field("Date completed", ukdate(c.end))
    add_distribution(nb, c)
    h, mi = clock(rng, 10, 19)
    return "Discharge Summary", nb, c.end, (h, mi)


# --------------------------------------------------------------------------
# Radiology report (RCR reporting standards)
# --------------------------------------------------------------------------
FINDINGS = {
    "XR": [],  # chosen by body part in build_radiology
    "CT": ["No acute intracranial abnormality.", "No focal lesion. No collection or free gas.",
           "No significant abnormality in the imaged region."],
    "MR": ["No significant abnormality.", "No focal signal abnormality. No cord compression."],
    "US": ["Normal appearances.", "No focal abnormality. No free fluid."],
    "MG": ["No suspicious mass, distortion or microcalcification. Breast density category B."],
    "FL": ["Satisfactory appearances on screening."],
}


def build_radiology(c: Ctx, proc: Mention):
    rng, d = c.rng, c.demo
    mod = modality(proc.name)
    interventional = any(w in proc.name.lower() for w in INTERVENTIONAL_WORDS)
    nb = NoteBuilder()
    nb.line("RADIOLOGY REPORT")
    nb.add("Examination: ")
    nb.term(proc)
    nb.line()
    nb.field("Date of examination", ukdate(c.start))
    nb.field("Patient", d.noun)

    nb.section("Clinical details")
    if c.conds:
        nb.term(c.conds[0])
        nb.line(". " + rng.choice(["Please assess.", "?Cause.", "Assess for complication."]))
    else:
        nb.line(rng.choice(["Routine.", "Not provided by referrer."]))

    if mod in ("CT", "MR", "FL") or interventional or "with contrast" in proc.name.lower():
        nb.section("Technique")
        nb.line("Contrast-enhanced, standard departmental protocol." if "contrast" in proc.name.lower()
                else "Standard departmental protocol.")

    nb.section("Comparison")
    prior = c.src.prior_imaging(c.v["person_id"], proc, c.start)
    nb.line(f"Previous study of {ukdate(prior)}." if prior else "No previous imaging available for comparison.")

    if interventional:
        nb.section("Procedure")
        nb.line("Informed consent obtained. WHO safety checklist completed. Procedure performed under "
                "image guidance without immediate complication.")
        nb.section("Aftercare")
        nb.line("Standard post-procedure observations. Contact the interventional radiology team if concerned.")
    else:
        nb.section("Findings")
        opts = FINDINGS[mod]
        if mod == "XR":
            opts = (["Lungs clear. Heart size normal. No pleural effusion.",
                     "No focal consolidation. No pneumothorax."] if "chest" in proc.name.lower()
                    else ["No acute bony injury.", "No focal abnormality.",
                          "Mild degenerative change. No acute abnormality."])
        nb.line(rng.choice(opts))
        if prior:
            nb.line("No significant interval change.")

    # RCR: a separate conclusion is not required for short reports
    # (plain radiographs, ultrasound, procedures).
    if mod in ("CT", "MR", "MG") and not interventional:
        nb.section("Conclusion")
        nb.line(rng.choice(["No acute abnormality.", "Normal study.",
                            "No imaging abnormality to account for the clinical presentation."]))

    nb.line()
    nb.line("Reported by: " + ("Consultant Interventional Radiologist" if interventional else
                               rng.choice(["Consultant Radiologist", "Reporting Radiographer"]
                                          if mod in ("XR", "US", "MG") else ["Consultant Radiologist"])))
    h, mi = clock(rng, 8, 20)
    return f"{mod} Report: {proc.name}"[:250], nb, c.start, (h, mi)


# --------------------------------------------------------------------------
# Main generation
# --------------------------------------------------------------------------
NOTE_COLS = ["note_id", "person_id", "note_date", "note_datetime", "note_type_concept_id",
             "note_class_concept_id", "note_title", "note_text", "encoding_concept_id",
             "language_concept_id", "provider_id", "visit_occurrence_id", "visit_detail_id",
             "note_source_value", "note_event_id", "note_event_field_concept_id"]
NLP_COLS = ["note_nlp_id", "note_id", "section_concept_id", "snippet", "offset", "lexical_variant",
            "note_nlp_concept_id", "note_nlp_source_concept_id", "nlp_system", "nlp_date",
            "nlp_datetime", "term_exists", "term_temporal", "term_modifiers"]


def snippet(text: str, start: int, length: int, window: int = 40) -> str:
    window = max(0, min(window, (230 - length) // 2))  # keep the whole term inside 250 chars
    a, b = max(0, start - window), min(len(text), start + length + window)
    s = " ".join(text[a:b].split())
    return s[:250]


def generate(src_dir: Path, out_dir: Path, seed: int, op_fraction: float) -> dict[str, int]:
    src = Source(src_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    visits = sorted(src.visits, key=lambda v: int(v["visit_occurrence_id"]))

    note_id = nlp_id = 0
    stats: dict[str, int] = defaultdict(int)
    with open(out_dir / "NOTE.csv", "w", newline="", encoding="utf-8") as fn, \
         open(out_dir / "NOTE_NLP.csv", "w", newline="", encoding="utf-8") as fl:
        wn = csv.writer(fn, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        wl = csv.writer(fl, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        wn.writerow(NOTE_COLS)
        wl.writerow(NLP_COLS)

        def emit(kind: str, v, title: str, nb: NoteBuilder, ndate: date, hm: tuple[int, int],
                 rng: random.Random):
            nonlocal note_id, nlp_id
            note_id += 1
            text = nb.text()
            ndt = datetime(ndate.year, ndate.month, ndate.day, *hm)
            cid, cname = NOTE_CLASS[kind]
            wn.writerow([note_id, v["person_id"], ndate.isoformat(), ndt.strftime("%Y-%m-%d %H:%M:%S"),
                         NOTE_TYPE_EHR, cid, title[:250], text, ENCODING_UTF8, LANGUAGE_ENGLISH,
                         "", v["visit_occurrence_id"], "", cname[:50], "", ""])
            stats[kind] += 1
            nlp_dt = ndt + timedelta(days=1, hours=rng.randint(0, 6))
            for sp in nb.spans:
                assert text[sp.start:sp.start + len(sp.text)] == sp.text
                nlp_id += 1
                wl.writerow([nlp_id, note_id, "", snippet(text, sp.start, len(sp.text)), sp.start,
                             sp.text[:250], sp.concept_id,
                             sp.source_concept_id if sp.source_concept_id is not None else NO_MATCHING_CONCEPT,
                             NLP_SYSTEM, nlp_dt.date().isoformat(), nlp_dt.strftime("%Y-%m-%d %H:%M:%S"),
                             sp.exists, sp.temporal, sp.modifiers[:2000]])

        for v in visits:
            if v["person_id"] not in src.persons or not parse_date(v["visit_start_date"]):
                continue
            vid = v["visit_occurrence_id"]
            rng = random.Random(f"{seed}:{vid}")
            vd = src.by_visit.get(vid, VisitData())
            c = Ctx.make(src, v, vd, rng, seed)
            vc = visit_kind(v)
            if vc == VISIT_IP:
                emit("admission", v, *build_admission(c), rng)
                emit("discharge", v, *build_discharge(c), rng)
            elif vc == VISIT_ER:
                emit("emergency", v, *build_emergency(c), rng)
            elif vc == VISIT_OP:
                has_content = vd.conditions or vd.procedures or vd.drugs
                if not has_content or rng.random() >= op_fraction:
                    continue
                emit("outpatient", v, *build_outpatient(c), rng)
            # Radiology reports for imaging procedures on any visit
            for p in c.procs:
                if is_imaging(p.name):
                    emit("radiology", v, *build_radiology(c, p), rng)

    stats["notes"] = note_id
    stats["note_nlp"] = nlp_id
    return dict(stats)


def ensure_note_concepts(concept_csv: Path) -> None:
    """Append any NOTE_CONCEPT_ROWS whose concept_id is missing from CONCEPT.csv.

    Existing rows are never modified: if a row with the same concept_id is
    already there (e.g. from a real Athena vocabulary) it is kept, and any
    difference from NOTE_CONCEPT_ROWS is only reported.
    """
    with open(concept_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        existing = {r["concept_id"]: r for r in reader}
    missing_cols = [c for c in NOTE_CONCEPT_ROWS[0] if c not in header]
    if missing_cols:
        raise SystemExit(f"{concept_csv}: missing column(s) {missing_cols}")

    to_add = []
    for row in NOTE_CONCEPT_ROWS:
        cid = str(row["concept_id"])
        have = existing.get(cid)
        if have is None:
            to_add.append(row)
            existing[cid] = {k: str(v) for k, v in row.items()}
            continue
        diffs = [k for k, v in row.items() if (have.get(k) or "") != str(v)]
        if diffs:
            print(f"  note: {concept_csv.name} already has concept {cid} ({have.get('concept_name')!r}); "
                  f"left as is (differs in {', '.join(diffs)})")

    if to_add:
        with open(concept_csv, "rb") as f:
            f.seek(-1, 2)
            needs_nl = f.read(1) != b"\n"
        with open(concept_csv, "a", newline="", encoding="utf-8") as f:
            if needs_nl:
                f.write("\n")
            w = csv.DictWriter(f, fieldnames=header, lineterminator="\n", extrasaction="ignore")
            for row in to_add:
                w.writerow({k: row.get(k, "") for k in header})
    print(f"{concept_csv}: {len(to_add)} concept(s) added, "
          f"{len(NOTE_CONCEPT_ROWS) - len(to_add)} already present")


def check_mappings(src_dir: Path) -> None:
    """Warn about mapped concept IDs that are in neither CONCEPT.csv nor NOTE_CONCEPT_ROWS."""
    known = {r["concept_id"] for r in read_csv(src_dir / "CONCEPT.csv")}
    known |= {str(r["concept_id"]) for r in NOTE_CONCEPT_ROWS}
    used = {"NOTE_TYPE_EHR": NOTE_TYPE_EHR, "ENCODING_UTF8": ENCODING_UTF8,
            "LANGUAGE_ENGLISH": LANGUAGE_ENGLISH, "NO_MATCHING_CONCEPT": NO_MATCHING_CONCEPT,
            "VISIT_IP": VISIT_IP, "VISIT_OP": VISIT_OP, "VISIT_ER": VISIT_ER,
            "GENDER_MALE": GENDER_MALE, "GENDER_FEMALE": GENDER_FEMALE,
            **{f"NOTE_CLASS[{k!r}]": cid for k, (cid, _) in NOTE_CLASS.items()}}
    for name, cid in used.items():
        if str(cid) not in known:
            print(f"  warning: {name} = {cid} is not in {src_dir / 'CONCEPT.csv'} or NOTE_CONCEPT_ROWS")
    names = [n for _, n in NOTE_CLASS.values() if len(n) > 50]
    if names:
        print(f"  warning: NOTE_CLASS names over 50 chars are truncated in note_source_value: {names}")


def install(out_dir: Path, repo: Path, update_concepts: bool) -> None:
    for ds in ("1000", "1001"):
        target = repo / "omop_lite" / "synthetic" / ds
        if not target.is_dir():
            print(f"skip {target} (missing)")
            continue
        shutil.copy2(out_dir / "NOTE.csv", target / "NOTE.csv")
        shutil.copy2(out_dir / "NOTE_NLP.csv", target / "NOTE_NLP.csv")
        print(f"installed NOTE.csv / NOTE_NLP.csv into {target}")
        if update_concepts:
            ensure_note_concepts(target / "CONCEPT.csv")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, required=True, help="omop_lite/synthetic/1001 (or 1000)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--op-fraction", type=float, default=1.0,
                    help="fraction of eligible outpatient visits that get a clinic letter (default 1.0)")
    ap.add_argument("--install", type=Path, help="path to a local omop-lite checkout to copy files into")
    ap.add_argument("--skip-concept-update", action="store_true",
                    help="do not append missing note concepts to CONCEPT.csv")
    a = ap.parse_args()
    check_mappings(a.source)
    stats = generate(a.source, a.out, a.seed, a.op_fraction)
    for k, val in sorted(stats.items()):
        print(f"{k:>12}: {val}")
    if not a.skip_concept_update:
        ensure_note_concepts(a.source / "CONCEPT.csv")
    if a.install:
        install(a.out, a.install, not a.skip_concept_update)


if __name__ == "__main__":
    main()