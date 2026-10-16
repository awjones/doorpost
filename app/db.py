"""SQLite storage: chore claims and approvals, and the screen time ledger."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS chore_status (
    day         TEXT NOT NULL,              -- YYYY-MM-DD, local date
    chore_id    TEXT NOT NULL,
    status      TEXT NOT NULL CHECK(status IN ('waiting', 'done')),
    claimed_at  TEXT,
    approved_at TEXT,
    approved_by TEXT,
    PRIMARY KEY (day, chore_id)
);

-- One row per approved chore: the chore history. (synced_at / sync_error are
-- left from when credits were sent to a separate screen time app; unused now.)
CREATE TABLE IF NOT EXISTS ledger (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    day         TEXT NOT NULL,
    chore_id    TEXT NOT NULL,
    kid         TEXT NOT NULL,
    title       TEXT NOT NULL,
    minutes     INTEGER NOT NULL,
    approved_at TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    synced_at   TEXT,
    sync_error  TEXT,
    UNIQUE (day, chore_id)
);

-- Screen time: every credit and deduction, who made it and when (see screentime.py).
-- `at` is naive local time. A week is everything since the latest new_week row.
CREATE TABLE IF NOT EXISTS screen_ledger (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    at        TEXT NOT NULL,
    kind      TEXT NOT NULL CHECK(kind IN ('chore', 'good_day', 'adjust', 'new_week')),
    minutes   INTEGER NOT NULL DEFAULT 0,          -- signed
    scope     TEXT NOT NULL DEFAULT 'family' CHECK(scope IN ('family', 'kid')),
    kid       TEXT,                                -- the frame's kid id
    note      TEXT NOT NULL DEFAULT '',
    by        TEXT NOT NULL,
    chore_day TEXT,
    chore_id  TEXT,
    undo_of   INTEGER REFERENCES screen_ledger(id),
    created   TEXT,
    UNIQUE (chore_day, chore_id)
);
CREATE INDEX IF NOT EXISTS screen_ledger_at ON screen_ledger(at);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
