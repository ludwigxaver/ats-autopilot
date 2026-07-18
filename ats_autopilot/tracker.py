"""
Idempotent application ledger (SQLite).

Records every application so the engine never double-applies and there's an audit trail of
what was prepared and submitted, when, and in what state.
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    key          TEXT PRIMARY KEY,   -- company:job_id
    ats          TEXT NOT NULL DEFAULT '',
    company      TEXT NOT NULL,
    title        TEXT NOT NULL,
    url          TEXT,
    status       TEXT NOT NULL,      -- prepared | review | submitted | interview | rejected | offer
    crown_jewel  INTEGER NOT NULL DEFAULT 0,
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass
class Tracker:
    db_path: str

    def __post_init__(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def seen(self, key: str) -> bool:
        with self._conn() as c:
            return c.execute("SELECT 1 FROM applications WHERE key=?", (key,)).fetchone() is not None

    def record(self, key: str, ats: str, company: str, title: str, url: str,
               status: str, crown_jewel: bool = False) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO applications(key,ats,company,title,url,status,crown_jewel) "
                "VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET status=excluded.status, "
                "updated_at=datetime('now')",
                (key, ats, company, title, url, status, int(crown_jewel)),
            )

    def all(self) -> list[tuple]:
        with self._conn() as c:
            return c.execute(
                "SELECT key,company,title,status,crown_jewel,updated_at "
                "FROM applications ORDER BY updated_at DESC"
            ).fetchall()

    def by_status(self, status: str) -> list[tuple]:
        with self._conn() as c:
            return c.execute(
                "SELECT key,ats,company,title,url,crown_jewel FROM applications "
                "WHERE status=? ORDER BY crown_jewel DESC, company",
                (status,),
            ).fetchall()
