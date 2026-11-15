"""SQLite access for the Advisor Agent (Sprint 1: custom SQL tool for the ReAct agent).

Builds ``sprints_learner.db`` from ``data/sprints_learner_db.csv`` and exposes
read-only LangChain tools. Curriculum mapping: Module 2 (SQL tools) and the
Career Services policy (eligibility rules for partner openings).

IMPORTANT (assumption): the client supplied no partner-openings data, so the
``partner_openings`` table is *synthetic seed data* generated here, clearly
marked ``is_synthetic = 1``. Replace it with the real feed when available.
"""
from __future__ import annotations

import csv
import json
import logging
import re
import sqlite3
from pathlib import Path

from langchain_core.tools import tool

from src import config
from src.schemas import UnableToVerify
from src.auth import require_learner

log = logging.getLogger("sprints.db")

# (role, min_modules, min_score, band_min_egp, band_max_egp) per track
_TRACK_ROLES = {
    "Advanced Agentic AI": ("Agentic AI Engineer", 10, 85, 25000, 48000),
    "Backend": ("Backend Engineer", 8, 75, 15000, 24000),
    "Frontend": ("Frontend Engineer", 12, 80, 11000, 20000),
    "Data Science": ("Data Scientist", 10, 80, 22000, 34000),
}
_PARTNER_BAND_FACTOR = {"Fawry": 1.0, "e& Egypt": 1.0, "Vodafone Egypt": 0.95, "Swvl": 0.9}

SCHEMA_DOC = (
    "Tables: learners(learner_id, name, bootcamp_track, completed_modules, python_assignment_score, "
    "target_salary_egp, preferred_employers, readiness_status); "
    "partner_openings(opening_id, partner, tier, role, track, min_modules, min_score, "
    "salary_min_egp, salary_max_egp, is_synthetic)."
)


def build_database(csv_path: Path = config.LEARNER_CSV, db_path: Path = config.LEARNER_DB) -> dict:
    """(Re)create the SQLite database from the learner CSV plus seed openings."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.executescript(
            """
            DROP TABLE IF EXISTS learners; DROP TABLE IF EXISTS partner_openings;
            CREATE TABLE learners(
              learner_id TEXT PRIMARY KEY, name TEXT NOT NULL, bootcamp_track TEXT NOT NULL,
              completed_modules INTEGER NOT NULL, python_assignment_score INTEGER NOT NULL,
              target_salary_egp INTEGER NOT NULL, preferred_employers TEXT NOT NULL,
              readiness_status TEXT NOT NULL);
            CREATE TABLE partner_openings(
              opening_id TEXT PRIMARY KEY, partner TEXT NOT NULL, tier INTEGER NOT NULL, role TEXT NOT NULL,
              track TEXT NOT NULL, min_modules INTEGER NOT NULL, min_score INTEGER NOT NULL,
              salary_min_egp INTEGER NOT NULL, salary_max_egp INTEGER NOT NULL, is_synthetic INTEGER NOT NULL DEFAULT 1);
            """
        )
        with open(csv_path, newline="", encoding="utf-8") as fh:
            rows = [
                (r["learner_id"], r["name"], r["bootcamp_track"], int(r["completed_modules"]),
                 int(r["python_assignment_score"]), int(r["target_salary_egp"]), r["preferred_employers"],
                 r["readiness_status"])
                for r in csv.DictReader(fh)
            ]
        con.executemany("INSERT INTO learners VALUES (?,?,?,?,?,?,?,?)", rows)
        openings = []
        for partner, factor in _PARTNER_BAND_FACTOR.items():
            tier = 1 if partner in config.TIER1_PARTNERS else 2
            for track, (role, mm, ms, lo, hi) in _TRACK_ROLES.items():
                code = "".join(w[0] for w in track.split()).upper()
                slug = re.sub(r"[^A-Za-z]", "", partner)[:4].upper()
                openings.append((f"OPN-{slug}-{code}", partner, tier, role, track, mm, ms,
                                 int(round(lo * factor, -2)), int(round(hi * factor, -2)), 1))
        con.executemany("INSERT INTO partner_openings VALUES (?,?,?,?,?,?,?,?,?,?)", openings)
    return {"learners": len(rows), "openings": len(openings), "db": str(db_path)}


def _connect_ro() -> sqlite3.Connection:
    """Open the database read-only (writes are impossible even if SQL is malicious)."""
    if not Path(config.LEARNER_DB).exists():
        build_database()
    con = sqlite3.connect(f"file:{config.LEARNER_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _fail(detail: str, source: str = "sqlite", message: str = "the learner database could not be queried") -> str:
    log.warning("DB tool failure: %s", detail)
    return UnableToVerify(source=source, message=message, detail=detail).model_dump_json()


# ------------------------------------------------------------------ tools
@tool
def get_learner_profile(learner_id: str) -> str:
    """Look up one learner's progress record in the Sprints learner database (SQLite).

    Returns JSON with completed_modules, python_assignment_score, target_salary_egp (monthly EGP),
    preferred_employers (list), bootcamp_track and readiness_status. Returns 'unable_to_verify' JSON
    if the learner does not exist or the database errors. Supports the Career Services placement flow.
    """
    try:
        learner_id = require_learner(learner_id)
        with _connect_ro() as con:
            row = con.execute("SELECT * FROM learners WHERE learner_id = ?", (learner_id.strip().upper(),)).fetchone()
        if row is None:
            return _fail(f"no learner with id {learner_id!r}", source="learner_record", message="no matching learner record")
        data = dict(row)
        data["preferred_employers"] = [e.strip() for e in data["preferred_employers"].split(",") if e.strip()]
        data["status"] = "ok"
        return json.dumps(data)
    except Exception as exc:  # graceful fallback (acceptance criterion)
        return _fail(str(exc))


def evaluate_openings(profile: dict) -> list[dict]:
    """Apply the six career-policy eligibility rules to every opening in the learner's track/employers.

    Returns one dict per candidate opening with ``eligible`` and ``reasons`` (why not). Pure function over
    DB rows - no model involved - so recommendations cannot be hallucinated.
    """
    require_learner(profile.get("learner_id", ""))
    with _connect_ro() as con:
        rows = [dict(r) for r in con.execute(
            "SELECT * FROM partner_openings WHERE track = ? ORDER BY partner", (profile["bootcamp_track"],))]
    out = []
    for o in rows:
        if o["partner"] not in profile["preferred_employers"]:
            continue
        reasons = []
        if profile["readiness_status"] != "Ready for Placement":
            reasons.append(f"readiness status is '{profile['readiness_status']}', not 'Ready for Placement'")
        if profile["completed_modules"] < o["min_modules"]:
            reasons.append(f"needs {o['min_modules']} modules, has {profile['completed_modules']}")
        if profile["python_assignment_score"] < o["min_score"]:
            reasons.append(f"needs Python score {o['min_score']}, has {profile['python_assignment_score']}")
        if profile["target_salary_egp"] > o["salary_max_egp"]:
            reasons.append(f"target {profile['target_salary_egp']} EGP is above the band maximum {o['salary_max_egp']} EGP")
        out.append({**o, "eligible": not reasons, "reasons": reasons})
    return out


@tool
def list_matching_openings(learner_id: str) -> str:
    """List partner openings for a learner with eligibility decisions computed from live database records.

    Applies the Career Services policy (track, preferred employer, modules, Python score, readiness and
    EGP salary band). Returns JSON {status, openings:[{opening_id, partner, tier, role, salary_min_egp,
    salary_max_egp, eligible, reasons}]} or 'unable_to_verify' JSON on any error.
    """
    try:
        prof = json.loads(get_learner_profile.invoke({"learner_id": learner_id}))
        if prof.get("status") != "ok":
            return json.dumps(prof)
        return json.dumps({"status": "ok", "learner_id": prof["learner_id"], "openings": evaluate_openings(prof)})
    except Exception as exc:
        return _fail(str(exc))


@tool
def run_readonly_sql(query: str) -> str:
    """Disabled legacy tool: learner requests must use scoped allowlisted operations."""
    return _fail("ad-hoc SQL is disabled", source="authorization", message="the SQL query was rejected")


run_readonly_sql.description += "\n" + SCHEMA_DOC
DB_TOOLS = [get_learner_profile, list_matching_openings]

if __name__ == "__main__":  # python -m src.tools.db_queries
    print(build_database())
