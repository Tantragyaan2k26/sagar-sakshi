"""
SAGAR-SAKSHI Data Layer - Database Connection & Session Engine (data_layer/database.py)
Provides persistent storage for incidents, pipeline runs, evidence cards, and analyst audit logs.
DATABASE_URL is currently not used; PostgreSQL/PostGIS support is not implemented here.
"""

import os
import sqlite3
import json
from typing import Any, Optional
from datetime import datetime, timezone

DB_PATH = os.environ.get("DATABASE_PATH", "runs/sagar_sakshi.db")
DATABASE_URL = os.environ.get("DATABASE_URL")


class Database:
    """Lightweight and robust persistent storage layer."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables for incidents, runs, reviews, and jobs (§4, §10)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Incidents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT,
                    aoi_json TEXT,
                    status TEXT DEFAULT 'active',
                    created_at_utc TEXT NOT NULL
                )
            """)

            # Evidence Runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    incident_id TEXT,
                    manifest_sha256 TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    ais_status TEXT,
                    posteriors_json TEXT NOT NULL,
                    evidence_terms_json TEXT,
                    exclusions_json TEXT,
                    metadata_json TEXT,
                    created_at_utc TEXT NOT NULL,
                    FOREIGN KEY (incident_id) REFERENCES incidents (incident_id)
                )
            """)

            # Analyst Reviews Audit Log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyst_reviews (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    notes TEXT,
                    timestamp_utc TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            """)

            # Pipeline Jobs table (SKIP LOCKED simulation)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_jobs (
                    job_id TEXT PRIMARY KEY,
                    scene_id TEXT,
                    config_path TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    error_log TEXT
                )
            """)
            conn.commit()

    def save_run(self, card_dict: dict[str, Any]):
        """Persists an EvidenceCard execution artifact."""
        run_id = card_dict["run_id"]
        attr = card_dict.get("attribution", {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO runs (
                    run_id, manifest_sha256, grade, headline,
                    ais_status, posteriors_json, evidence_terms_json,
                    exclusions_json, metadata_json, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    manifest_sha256 = excluded.manifest_sha256,
                    grade = excluded.grade,
                    headline = excluded.headline,
                    ais_status = excluded.ais_status,
                    posteriors_json = excluded.posteriors_json,
                    evidence_terms_json = excluded.evidence_terms_json,
                    exclusions_json = excluded.exclusions_json,
                    metadata_json = excluded.metadata_json,
                    created_at_utc = excluded.created_at_utc
            """, (
                run_id,
                card_dict.get("manifest_sha256", ""),
                attr.get("grade", "None"),
                attr.get("headline", ""),
                card_dict.get("ais_status", "synthetic"),
                json.dumps(attr.get("posteriors", {})),
                json.dumps(attr.get("evidence_terms", {})),
                json.dumps(attr.get("exclusions", [])),
                json.dumps(card_dict.get("metadata", {})),
                card_dict.get("generated_at_utc", datetime.now(timezone.utc).isoformat()),
            ))
            conn.commit()

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a run by run_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "run_id": row["run_id"],
                "manifest_sha256": row["manifest_sha256"],
                "attribution": {
                    "schema_version": "1.0",
                    "run_id": row["run_id"],
                    "posteriors": json.loads(row["posteriors_json"]),
                    "evidence_terms": json.loads(row["evidence_terms_json"] or "{}"),
                    "grade": row["grade"],
                    "exclusions": json.loads(row["exclusions_json"] or "[]"),
                    "headline": row["headline"],
                },
                "ais_status": row["ais_status"],
                "generated_at_utc": row["created_at_utc"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }

    def record_review(self, run_id: str, reviewer_id: str, decision: str, notes: Optional[str] = None) -> dict[str, Any]:
        """Records an official audited analyst review."""
        now_utc = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analyst_reviews (run_id, reviewer_id, decision, notes, timestamp_utc)
                VALUES (?, ?, ?, ?, ?)
            """, (run_id, reviewer_id, decision, notes, now_utc))
            conn.commit()
            rev_id = cursor.lastrowid
            return {
                "review_id": rev_id,
                "run_id": run_id,
                "reviewer_id": reviewer_id,
                "decision": decision,
                "notes": notes,
                "timestamp_utc": now_utc,
            }

    def list_reviews_for_run(self, run_id: str) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analyst_reviews WHERE run_id = ? ORDER BY review_id DESC", (run_id,))
            return [dict(r) for r in cursor.fetchall()]

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT run_id, grade, headline, manifest_sha256, created_at_utc FROM runs ORDER BY created_at_utc DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]


# Global database instance
db = Database()
