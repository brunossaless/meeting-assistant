"""SQLite storage for meetings (transcript + análise)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "meetings.db"

_JSON_FIELD_MAP = {
    "transcript_json": "transcript",
    "topics_json": "topics",
    "modules_json": "modules",
    "participants_json": "participants_mentioned",
    "action_items_json": "action_items",
}


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL DEFAULT 'recording',
                mic_path TEXT,
                system_path TEXT,
                transcript_json TEXT,
                summary TEXT,
                topics_json TEXT,
                project TEXT,
                modules_json TEXT,
                participants_json TEXT,
                action_items_json TEXT,
                closing_summary TEXT,
                error_message TEXT
            );
            """
        )
        existing_columns = {row["name"] for row in c.execute("PRAGMA table_info(meetings)")}
        if "closing_summary" not in existing_columns:
            c.execute("ALTER TABLE meetings ADD COLUMN closing_summary TEXT")


def create_meeting(meeting_id: str, started_at: str, mic_path: str, system_path: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO meetings (id, started_at, status, mic_path, system_path) "
            "VALUES (?, ?, 'recording', ?, ?)",
            (meeting_id, started_at, mic_path, system_path),
        )


def set_ended(meeting_id: str, ended_at: str) -> None:
    with _conn() as c:
        c.execute("UPDATE meetings SET ended_at = ? WHERE id = ?", (ended_at, meeting_id))


def set_status(meeting_id: str, status: str, error_message: Optional[str] = None) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE meetings SET status = ?, error_message = ? WHERE id = ?",
            (status, error_message, meeting_id),
        )


def save_transcript(meeting_id: str, segments: list[dict]) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE meetings SET transcript_json = ? WHERE id = ?",
            (json.dumps(segments, ensure_ascii=False), meeting_id),
        )


def save_analysis(meeting_id: str, analysis: dict) -> None:
    with _conn() as c:
        c.execute(
            """
            UPDATE meetings SET
                status = 'done',
                summary = ?,
                topics_json = ?,
                project = ?,
                modules_json = ?,
                participants_json = ?,
                action_items_json = ?,
                closing_summary = ?
            WHERE id = ?
            """,
            (
                analysis.get("summary"),
                json.dumps(analysis.get("topics", []), ensure_ascii=False),
                analysis.get("project"),
                json.dumps(analysis.get("modules", []), ensure_ascii=False),
                json.dumps(analysis.get("participants_mentioned", []), ensure_ascii=False),
                json.dumps(analysis.get("action_items", []), ensure_ascii=False),
                analysis.get("closing_summary"),
                meeting_id,
            ),
        )


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for json_field, out_field in _JSON_FIELD_MAP.items():
        raw = d.pop(json_field, None)
        d[out_field] = json.loads(raw) if raw else []
    return d


def get_meeting(meeting_id: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_meetings() -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, started_at, ended_at, status, project, summary "
            "FROM meetings ORDER BY started_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]
