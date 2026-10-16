"""Daily chores: who has what today, and the claim -> approve flow.

A chore is "todo" until a kid taps "I did it" (-> "waiting"). Only a parent
(PIN on the frame, or the phone page) can move it to "done", which writes a
chore-history row and credits the screen time ledger in the same transaction.
Kids can never add minutes themselves.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from .config import DAY_KEYS, ChoreDef, Settings
from .db import Database
from .screentime import record_chore


class ChoreError(Exception):
    pass


def week_bounds(day: date) -> tuple[date, date]:
    """Monday..Sunday, matching the screen time app's week."""
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def scheduled(settings: Settings, day: date, kid: str | None = None) -> list[ChoreDef]:
    key = DAY_KEYS[day.weekday()]
    return [c for c in settings.chores if key in c.days and (kid is None or c.kid == kid)]


def _find(settings: Settings, chore_id: str, day: date) -> ChoreDef:
    for c in scheduled(settings, day):
        if c.id == chore_id:
            return c
    raise ChoreError("That chore isn't on today's list.")


def chores_for(db: Database, settings: Settings, day: date, kid: str | None = None) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM chore_status WHERE day = ?", (day.isoformat(),)).fetchall()
    status = {r["chore_id"]: dict(r) for r in rows}
    out = []
    for c in scheduled(settings, day, kid):
        s = status.get(c.id)
        out.append({
            "id": c.id, "kid": c.kid, "title": c.title, "minutes": c.minutes,
            "status": s["status"] if s else "todo",
            "claimed_at": s["claimed_at"] if s else None,
        })
    return out


def claim(db: Database, settings: Settings, chore_id: str, day: date, now: datetime) -> str:
    _find(settings, chore_id, day)
    with db.connect() as conn:
        row = conn.execute("SELECT status FROM chore_status WHERE day=? AND chore_id=?",
                           (day.isoformat(), chore_id)).fetchone()
        if row:
            return row["status"]
        conn.execute("INSERT INTO chore_status (day, chore_id, status, claimed_at) VALUES (?,?,?,?)",
                     (day.isoformat(), chore_id, "waiting", now.isoformat(timespec="seconds")))
    return "waiting"


def send_back(db: Database, chore_id: str, day: date) -> None:
    """Parent says 'not yet': the chore goes back to the kid's to-do list."""
    with db.connect() as conn:
        conn.execute("DELETE FROM chore_status WHERE day=? AND chore_id=? AND status='waiting'",
                     (day.isoformat(), chore_id))


def approve(db: Database, settings: Settings, chore_id: str, day: date, now: datetime,
            approved_by: str) -> dict:
    c = _find(settings, chore_id, day)
    stamp = now.isoformat(timespec="seconds")
    with db.connect() as conn:
        row = conn.execute("SELECT status FROM chore_status WHERE day=? AND chore_id=?",
                           (day.isoformat(), chore_id)).fetchone()
        if row and row["status"] == "done":
            raise ChoreError("Already approved.")
        conn.execute(
            """INSERT INTO chore_status (day, chore_id, status, claimed_at, approved_at, approved_by)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(day, chore_id) DO UPDATE SET status='done', approved_at=excluded.approved_at,
                   approved_by=excluded.approved_by""",
            (day.isoformat(), chore_id, "done", stamp, stamp, approved_by))
        conn.execute(
            """INSERT OR IGNORE INTO ledger (day, chore_id, kid, title, minutes, approved_at, approved_by)
               VALUES (?,?,?,?,?,?,?)""",
            (day.isoformat(), chore_id, c.kid, c.title, c.minutes, stamp, approved_by))
        record_chore(conn, day, chore_id, c.kid, c.title, c.minutes, now, approved_by)
    return {"id": c.id, "kid": c.kid, "title": c.title, "minutes": c.minutes}


def waiting(db: Database, settings: Settings, day: date) -> list[dict]:
    return [c for c in chores_for(db, settings, day) if c["status"] == "waiting"]


def local_week_minutes(db: Database, kid: str, day: date) -> dict[str, int]:
    """Minutes approved on the frame this week, by weekday (mon..sun)."""
    start, end = week_bounds(day)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT day, SUM(minutes) AS m FROM ledger WHERE kid=? AND day BETWEEN ? AND ? GROUP BY day",
            (kid, start.isoformat(), end.isoformat())).fetchall()
    out = {k: 0 for k in DAY_KEYS}
    for r in rows:
        out[DAY_KEYS[date.fromisoformat(r["day"]).weekday()]] = r["m"]
    return out
