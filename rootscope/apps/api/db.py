"""SQLite persistence for incidents, events, diagnoses, and artifacts."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from agent.schemas import Artifact, Diagnosis, Evidence, InvestigationEvent, ProposedFix

def db_path() -> Path:
    return Path(os.environ.get("ROOTSCOPE_DATABASE", "data/rootscope.db"))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                source TEXT NOT NULL,
                demo_key TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                label TEXT NOT NULL,
                state TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnoses (
                incident_id TEXT PRIMARY KEY,
                root_cause TEXT NOT NULL,
                confidence TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                affected_services_json TEXT NOT NULL,
                affected_files_json TEXT NOT NULL,
                proposed_fix_json TEXT NOT NULL,
                test_result TEXT,
                git_diff TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                incident_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                body_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (incident_id, kind)
            )
            """
        )


def next_incident_id() -> str:
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM incidents").fetchone()
    return f"RS-{1042 + int(row['n'])}"


def set_status(incident_id: str, status: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE incidents SET status = ? WHERE id = ?",
            (status, incident_id),
        )


def clear_investigation(incident_id: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM events WHERE incident_id = ?", (incident_id,))
        conn.execute("DELETE FROM diagnoses WHERE incident_id = ?", (incident_id,))
        conn.execute("DELETE FROM artifacts WHERE incident_id = ?", (incident_id,))


def append_event(
    incident_id: str, label: str, state: str, detail: Optional[str] = None
) -> InvestigationEvent:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS n FROM events WHERE incident_id = ?",
            (incident_id,),
        ).fetchone()
        seq = int(row["n"]) + 1
        conn.execute(
            """
            INSERT INTO events (incident_id, seq, label, state, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (incident_id, seq, label, state, detail, now),
        )
    return InvestigationEvent(
        incident_id=incident_id,
        seq=seq,
        label=label,
        state=state,
        detail=detail,
        created_at=now,
    )


def list_events(incident_id: str) -> List[InvestigationEvent]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE incident_id = ? ORDER BY seq",
            (incident_id,),
        ).fetchall()
    return [InvestigationEvent(**dict(row)) for row in rows]


def save_diagnosis(diagnosis: Diagnosis) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO diagnoses
            (incident_id, root_cause, confidence, evidence_json,
             affected_services_json, affected_files_json, proposed_fix_json,
             test_result, git_diff, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                diagnosis.incident_id,
                diagnosis.root_cause,
                diagnosis.confidence,
                json.dumps([item.model_dump() for item in diagnosis.evidence]),
                json.dumps(diagnosis.affected_services),
                json.dumps(diagnosis.affected_files),
                json.dumps(diagnosis.proposed_fix.model_dump()),
                diagnosis.test_result,
                diagnosis.git_diff,
                now,
            ),
        )


def load_diagnosis(incident_id: str) -> Optional[Diagnosis]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM diagnoses WHERE incident_id = ?",
            (incident_id,),
        ).fetchone()
    if row is None:
        return None
    return Diagnosis(
        incident_id=row["incident_id"],
        root_cause=row["root_cause"],
        confidence=row["confidence"],
        evidence=[Evidence(**item) for item in json.loads(row["evidence_json"])],
        affected_services=json.loads(row["affected_services_json"]),
        affected_files=json.loads(row["affected_files_json"]),
        proposed_fix=ProposedFix(**json.loads(row["proposed_fix_json"])),
        test_result=row["test_result"],
        git_diff=row["git_diff"],
    )


def save_artifact(artifact: Artifact) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO artifacts
            (incident_id, kind, body_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                artifact.incident_id,
                artifact.kind,
                json.dumps(artifact.body),
                artifact.created_at,
            ),
        )


def list_artifacts(incident_id: str) -> List[Artifact]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM artifacts WHERE incident_id = ? ORDER BY kind",
            (incident_id,),
        ).fetchall()
    return [
        Artifact(
            incident_id=row["incident_id"],
            kind=row["kind"],
            body=json.loads(row["body_json"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]
