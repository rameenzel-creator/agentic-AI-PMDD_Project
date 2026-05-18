"""
Episodic Memory — SQLite-based persistent store.
Agents write and query past analysis decisions to learn over time.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "memory.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all required tables if they don't exist."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE NOT NULL,
            corpus_name TEXT,
            corpus_size INTEGER,
            created_at TEXT,
            drift_score REAL,
            summary TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_id INTEGER NOT NULL,
            segment_id INTEGER,
            decision_type TEXT,
            decision_data TEXT,
            confidence REAL,
            self_corrected INTEGER DEFAULT 0,
            correction_reason TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS lessons_learned (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            keyword TEXT,
            context_type TEXT,
            learned_field TEXT,
            frequency INTEGER DEFAULT 1,
            updated_at TEXT
        );
    """)
    conn.commit()
    conn.close()


def save_run(run_id: str, corpus_name: str, corpus_size: int) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO analysis_runs (run_id, corpus_name, corpus_size, created_at) VALUES (?, ?, ?, ?)",
        (run_id, corpus_name, corpus_size, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def update_run_score(run_id: str, drift_score: float, summary: str) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE analysis_runs SET drift_score=?, summary=? WHERE run_id=?",
        (drift_score, summary, run_id),
    )
    conn.commit()
    conn.close()


def save_decision(
    run_id: str,
    agent_id: int,
    segment_id: int,
    decision_type: str,
    decision_data: dict,
    confidence: float = 1.0,
    self_corrected: bool = False,
    correction_reason: str = "",
) -> None:
    conn = _get_conn()
    conn.execute(
        """INSERT INTO agent_decisions
           (run_id, agent_id, segment_id, decision_type, decision_data, confidence,
            self_corrected, correction_reason, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            agent_id,
            segment_id,
            decision_type,
            json.dumps(decision_data),
            confidence,
            int(self_corrected),
            correction_reason,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_past_lessons(agent_id: int, keyword: str) -> list[dict]:
    """Retrieve historical context for a keyword to guide the agent."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT learned_field, context_type, frequency
           FROM lessons_learned
           WHERE agent_id=? AND keyword LIKE ?
           ORDER BY frequency DESC LIMIT 10""",
        (agent_id, f"%{keyword}%"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_lesson(agent_id: int, keyword: str, context_type: str, learned_field: str) -> None:
    """Upsert a lesson learned entry."""
    conn = _get_conn()
    existing = conn.execute(
        "SELECT id, frequency FROM lessons_learned WHERE agent_id=? AND keyword=? AND learned_field=?",
        (agent_id, keyword, learned_field),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE lessons_learned SET frequency=?, updated_at=? WHERE id=?",
            (existing["frequency"] + 1, datetime.utcnow().isoformat(), existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO lessons_learned (agent_id, keyword, context_type, learned_field, updated_at) VALUES (?, ?, ?, ?, ?)",
            (agent_id, keyword, context_type, learned_field, datetime.utcnow().isoformat()),
        )
    conn.commit()
    conn.close()


def get_recent_runs(limit: int = 10) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM analysis_runs ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
