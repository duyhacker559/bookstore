import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


CREATE_EVENTS_SQL = """
CREATE TABLE IF NOT EXISTS behavior_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT,
    event_type TEXT NOT NULL,
    product_id INTEGER,
    category TEXT,
    query_text TEXT,
    metadata_json TEXT,
    ts TEXT NOT NULL
)
"""


class BehaviorStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(CREATE_EVENTS_SQL)
            conn.commit()

    def insert_events(self, events: Iterable[Dict[str, Any]]) -> int:
        rows = []
        for e in events:
            rows.append(
                (
                    int(e["user_id"]),
                    e.get("session_id"),
                    str(e["event_type"]),
                    e.get("product_id"),
                    e.get("category"),
                    e.get("query_text"),
                    json.dumps(e.get("metadata") or {}, ensure_ascii=False),
                    (e.get("ts") or datetime.utcnow()).isoformat(),
                )
            )

        if not rows:
            return 0

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO behavior_events
                (user_id, session_id, event_type, product_id, category, query_text, metadata_json, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    def total_events(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM behavior_events").fetchone()
            return int(row["c"] if row else 0)

    def events_for_user(self, user_id: int, limit: int = 200) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM behavior_events
                WHERE user_id = ?
                ORDER BY datetime(ts) DESC
                LIMIT ?
                """,
                (int(user_id), int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]

    def all_events(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM behavior_events ORDER BY datetime(ts) DESC").fetchall()
        return [dict(r) for r in rows]

    def event_type_counts(self) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type, COUNT(*) AS c
                FROM behavior_events
                GROUP BY event_type
                ORDER BY c DESC
                """
            ).fetchall()
        return {str(r["event_type"]): int(r["c"]) for r in rows}

    def category_counts(self) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT COALESCE(NULLIF(category, ''), 'unknown') AS cat, COUNT(*) AS c
                FROM behavior_events
                GROUP BY cat
                ORDER BY c DESC
                """
            ).fetchall()
        return {str(r["cat"]): int(r["c"]) for r in rows}
