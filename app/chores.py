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


# ---------------- approving later in the week ----------------
# A chore a kid marked done but nobody approved by midnight stays approvable for the rest of
# the screen time week (the parent page, and the email's quick approve buttons). It counts
# toward the week it is approved in.

def earliest_day(db: Database, today: date) -> date:
    """The first day whose waiting chores can still be approved: the start of this screen
    time week (a week started in the evening begins the next day), and never over 6 days back."""
    with db.connect() as conn:
        row = conn.execute("SELECT MAX(at) AS at FROM screen_ledger WHERE kind='new_week'").fetchone()
    first = today - timedelta(days=6)
    if row and row["at"]:
        start = datetime.fromisoformat(row["at"])
        begins = start.date() if start.time() == datetime.min.time() else start.date() + timedelta(days=1)
        first = max(first, begins)
    return min(first, today)


def waiting_since(db: Database, settings: Settings, first: date, last: date) -> list[dict]:
    """Waiting chores from `first` through `last` (oldest first), each with its day."""
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM chore_status WHERE status='waiting' AND day BETWEEN ? AND ? ORDER BY day, claimed_at",
                            (first.isoformat(), last.isoformat())).fetchall()
    out = []
    for r in rows:
        d = date.fromisoformat(r["day"])
        c = next((c for c in scheduled(settings, d) if c.id == r["chore_id"]), None)
        if c:
            out.append({"id": c.id, "kid": c.kid, "title": c.title, "minutes": c.minutes, "status": "waiting",
                        "day": r["day"], "claimed_at": r["claimed_at"]})
    return out


def check_day(db: Database, settings: Settings, chore_id: str, day: date, today: date) -> None:
    """A day other than today: the chore must still be waiting, and the day in this week."""
    if day == today:
        return
    if day > today or day < earliest_day(db, today):
        raise ChoreError("That day is outside this screen time week.")
    with db.connect() as conn:
        row = conn.execute("SELECT status FROM chore_status WHERE day=? AND chore_id=?",
                           (day.isoformat(), chore_id)).fetchone()
    if not row or row["status"] != "waiting":
        raise ChoreError("Only a chore that is waiting can be approved on a later day.")


def approve_on(db: Database, settings: Settings, chore_id: str, day: date, now: datetime, approved_by: str) -> dict:
    """approve() for today or an earlier day this week."""
    check_day(db, settings, chore_id, day, now.date())
    return approve(db, settings, chore_id, day, now, approved_by)


def unapprove(db: Database, settings: Settings, chore_id: str, day: date, now: datetime, by: str) -> dict:
    """Undo an approval (the email page's Undo): the chore waits again and its minutes come off
    with an opposite screen time row. The credit row stays in the log, marked undone."""
    c = _find(settings, chore_id, day)
    with db.connect() as conn:
        row = conn.execute("SELECT status FROM chore_status WHERE day=? AND chore_id=?",
                           (day.isoformat(), chore_id)).fetchone()
        if not row or row["status"] != "done":
            raise ChoreError("That chore isn't approved.")
        credit = conn.execute("SELECT * FROM screen_ledger WHERE kind='chore' AND chore_day=? AND chore_id=?",
                              (day.isoformat(), chore_id)).fetchone()
        conn.execute("UPDATE chore_status SET status='waiting', approved_at=NULL, approved_by=NULL WHERE day=? AND chore_id=?",
                     (day.isoformat(), chore_id))
        conn.execute("DELETE FROM ledger WHERE day=? AND chore_id=?", (day.isoformat(), chore_id))
        if credit:
            stamp = now.replace(tzinfo=None, microsecond=0).isoformat()
            conn.execute(
                """INSERT INTO screen_ledger (at, kind, minutes, scope, kid, note, by, undo_of)
                   VALUES (?, 'adjust', ?, 'family', ?, ?, ?, ?)""",
                (stamp, -credit["minutes"], credit["kid"], f"Undid: {credit['note']}", by, credit["id"]))
            # free the chore's one-credit-per-day slot, so approving it again credits it again
            conn.execute("UPDATE screen_ledger SET chore_id = chore_id || '#undone-' || id WHERE id = ?", (credit["id"],))
    return {"id": c.id, "kid": c.kid, "title": c.title, "minutes": c.minutes}


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
