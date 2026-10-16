"""Screen time: the family's weekly ledger.

Moved in from the separate screen time app (October 2026), keeping its rules:
kids earn during the week and the family spends it on the weekend, from one
shared pool. Every change is a row in `screen_ledger`, stamped with the parent
who made it, so the log is the record:

- chore      an approved chore. Into the family pool, with that kid as contributor.
- good_day   a parent's one-tap "good day for everyone" (30 min by default).
- adjust     a parent adds or takes away minutes, for everyone or one kid. A kid's
             adjustment either goes into the family pool (the kid gets credit) or
             is "just for" that kid.
- new_week   a parent starts a new week. Nothing resets by itself: the phone page
             and the frame's parent panel remind after the set time (Sunday 9 PM).

Base weekend time (Saturday + Sunday) isn't a row; it's added on top of the pool.
Times are stored as naive local ISO strings so they sort correctly across DST.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from .db import Database
from .timeutil import fmt_minutes

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
VIEWS = ["leader", "vault", "rocket", "glass"]
MAX_ADJUST = 240
SYSTEM = "Doorpost"


class ScreenTimeError(Exception):
    pass


@dataclass
class ScreenTimeSettings:
    base_saturday_minutes: int = 90
    base_sunday_minutes: int = 90
    good_day_minutes: int = 30
    full_minutes: int = 480          # where the vault, fuel tank and hourglass read "full"
    new_week_day: str = "sun"        # when the "start a new week" reminder appears
    new_week_time: str = "21:00"
    views: list[str] = field(default_factory=lambda: list(VIEWS))

    @classmethod
    def from_store(cls, st: dict) -> "ScreenTimeSettings":
        st = st or {}
        out = cls()
        if "base_saturday_minutes" not in st and st.get("weekend_base_minutes"):
            # the old setting was one number for the whole weekend
            total = int(st["weekend_base_minutes"])
            out.base_saturday_minutes, out.base_sunday_minutes = total - total // 2, total // 2
        for k in ("base_saturday_minutes", "base_sunday_minutes", "good_day_minutes", "full_minutes"):
            if st.get(k) not in (None, ""):
                setattr(out, k, int(st[k]))
        if st.get("new_week_day") in DAY_KEYS:
            out.new_week_day = st["new_week_day"]
        if st.get("new_week_time"):
            out.new_week_time = str(st["new_week_time"])
        views = [v for v in (st.get("views") or []) if v in VIEWS]
        if views:
            out.views = views
        return out

    def to_store(self) -> dict:
        return {"base_saturday_minutes": self.base_saturday_minutes, "base_sunday_minutes": self.base_sunday_minutes,
                "good_day_minutes": self.good_day_minutes, "full_minutes": self.full_minutes,
                "new_week_day": self.new_week_day, "new_week_time": self.new_week_time, "views": list(self.views)}

    @property
    def base_minutes(self) -> int:
        return self.base_saturday_minutes + self.base_sunday_minutes


def local(dt: datetime) -> str:
    """Naive local ISO, seconds precision."""
    return dt.replace(tzinfo=None, microsecond=0).isoformat()


def _parse(at: str) -> datetime:
    return datetime.fromisoformat(at).replace(tzinfo=None)


def week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


# ---------------- writes ----------------

def ensure_started(db: Database, now: datetime) -> None:
    """First run: open this week at Monday 00:00 and carry in this week's chore approvals."""
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM screen_ledger LIMIT 1").fetchone():
            return
        monday = week_monday(now.date())
        conn.execute("INSERT INTO screen_ledger (at, kind, minutes, note, by) VALUES (?, 'new_week', 0, ?, ?)",
                     (f"{monday.isoformat()}T00:00:00", "Screen time started on the frame", SYSTEM))
        rows = conn.execute("SELECT * FROM ledger WHERE day >= ? ORDER BY id", (monday.isoformat(),)).fetchall()
        for r in rows:
            conn.execute(
                """INSERT OR IGNORE INTO screen_ledger (at, kind, minutes, scope, kid, note, by, chore_day, chore_id)
                   VALUES (?, 'chore', ?, 'family', ?, ?, ?, ?, ?)""",
                (local(datetime.fromisoformat(r["approved_at"])), r["minutes"], r["kid"], r["title"],
                 r["approved_by"], r["day"], r["chore_id"]))


def record_chore(conn, day: date, chore_id: str, kid: str, title: str, minutes: int, at: datetime, by: str) -> None:
    """Called inside the chore approval's own transaction, so the two can't disagree."""
    conn.execute(
        """INSERT OR IGNORE INTO screen_ledger (at, kind, minutes, scope, kid, note, by, chore_day, chore_id)
           VALUES (?, 'chore', ?, 'family', ?, ?, ?, ?, ?)""",
        (local(at), minutes, kid, title, by, day.isoformat(), chore_id))


def good_day(db: Database, cfg: ScreenTimeSettings, now: datetime, by: str) -> dict:
    with db.connect() as conn:
        start = _week_start(conn)
        today = now.date().isoformat()
        dup = conn.execute(
            """SELECT by FROM screen_ledger s WHERE kind='good_day' AND at >= ? AND substr(at, 1, 10) = ?
               AND NOT EXISTS (SELECT 1 FROM screen_ledger u WHERE u.undo_of = s.id)""", (start, today)).fetchone()
        if dup:
            raise ScreenTimeError(f"{dup['by']} already gave today's good day.")
        cur = conn.execute("INSERT INTO screen_ledger (at, kind, minutes, note, by) VALUES (?, 'good_day', ?, ?, ?)",
                           (local(now), cfg.good_day_minutes, "A good day for everyone", by))
        return {"id": cur.lastrowid, "minutes": cfg.good_day_minutes}


def adjust(db: Database, now: datetime, by: str, minutes: int, kid: Optional[str], scope: str, note: str) -> dict:
    minutes = int(minutes)
    if not minutes or abs(minutes) > MAX_ADJUST:
        raise ScreenTimeError(f"Pick an amount between -{MAX_ADJUST} and +{MAX_ADJUST} minutes.")
    if scope not in ("family", "kid"):
        raise ScreenTimeError("Choose the family pool or just one kid.")
    if scope == "kid" and not kid:
        raise ScreenTimeError("Pick which kid this is just for.")
    note = (note or "").strip()[:80] or ("Extra time" if minutes > 0 else "Time taken away")
    with db.connect() as conn:
        cur = conn.execute("INSERT INTO screen_ledger (at, kind, minutes, scope, kid, note, by) VALUES (?, 'adjust', ?, ?, ?, ?, ?)",
                           (local(now), minutes, scope, kid or None, note, by))
        return {"id": cur.lastrowid, "minutes": minutes}


def undo(db: Database, entry_id: int, now: datetime, by: str) -> dict:
    """Reverse a good day or an adjustment with an opposite row. Nothing is deleted."""
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM screen_ledger WHERE id = ?", (entry_id,)).fetchone()
        if not row or row["kind"] not in ("good_day", "adjust") or row["undo_of"]:
            raise ScreenTimeError("Only a good day or an added/taken-away entry can be undone.")
        if row["at"] < _week_start(conn):
            raise ScreenTimeError("That's from an earlier week.")
        if conn.execute("SELECT 1 FROM screen_ledger WHERE undo_of = ?", (entry_id,)).fetchone():
            raise ScreenTimeError("Already undone.")
        cur = conn.execute(
            """INSERT INTO screen_ledger (at, kind, minutes, scope, kid, note, by, undo_of)
               VALUES (?, 'adjust', ?, ?, ?, ?, ?, ?)""",
            (local(now), -row["minutes"], row["scope"], row["kid"], f"Undid: {row['note']}", by, entry_id))
        return {"id": cur.lastrowid}


def new_week(db: Database, cfg: ScreenTimeSettings, now: datetime, by: str, last_total: Optional[int] = None) -> dict:
    """Start a new week. If the reminder time has passed, the week starts from then, so
    Monday-morning chores approved before anyone pressed the button land in the new week."""
    naive_now = now.replace(tzinfo=None)
    with db.connect() as conn:
        latest = conn.execute("SELECT at, created FROM screen_ledger WHERE kind='new_week' ORDER BY id DESC LIMIT 1").fetchone()
        if latest and latest["created"] and naive_now - _parse(latest["created"]) < timedelta(minutes=10):
            return {"started": latest["at"], "already": True}   # a double tap, or both parents at once
        due = reminder_at(cfg, _parse(_week_start(conn)))
        begin = due if naive_now >= due else naive_now
        note = "New week" + (f" (last week: {fmt_minutes(last_total)})" if last_total is not None else "")
        conn.execute("INSERT INTO screen_ledger (at, kind, minutes, note, by, created) VALUES (?, 'new_week', 0, ?, ?, ?)",
                     (local(begin), note, by, local(now)))
        return {"started": local(begin), "already": False}


# ---------------- reads ----------------

def _week_start(conn) -> str:
    row = conn.execute("SELECT MAX(at) AS at FROM screen_ledger WHERE kind='new_week'").fetchone()
    return row["at"] or "2000-01-01T00:00:00"  # not started yet: everything counts


def reminder_at(cfg: ScreenTimeSettings, week_start: datetime) -> datetime:
    """The first reminder moment (e.g. Sunday 9 PM) after the week started."""
    h, m = (int(x) for x in cfg.new_week_time.split(":"))
    target = DAY_KEYS.index(cfg.new_week_day)
    d = week_start.date() + timedelta(days=(target - week_start.weekday()) % 7)
    at = datetime(d.year, d.month, d.day, h, m)
    if at <= week_start:
        at += timedelta(days=7)
    return at


def week_rows(db: Database) -> tuple[str, Optional[dict], list[dict]]:
    with db.connect() as conn:
        start = _week_start(conn)
        marker = conn.execute("SELECT * FROM screen_ledger WHERE kind='new_week' AND at = ? ORDER BY id DESC LIMIT 1",
                              (start,)).fetchone()
        rows = conn.execute("SELECT * FROM screen_ledger WHERE kind != 'new_week' AND at >= ? ORDER BY at, id",
                            (start,)).fetchall()
        undone = {r["undo_of"] for r in rows if r["undo_of"]}
    return start, (dict(marker) if marker else None), [dict(r, undone=r["id"] in undone) for r in rows]


def _first(name: str) -> str:
    return (name or "").split(" (")[0].split(" ")[0] or name


def summary(db: Database, cfg: ScreenTimeSettings, kids: list, now: datetime) -> dict:
    """Everything the frame, the phone page and the settings overview show."""
    start, marker, rows = week_rows(db)
    kid_ids = [k.id for k in kids]
    names = {k.id: k.name for k in kids}
    kind_of = {r["id"]: r["kind"] for r in rows}
    for r in rows:  # an undo counts under what it undid
        r["eff"] = kind_of.get(r["undo_of"], "adjust") if r["undo_of"] else r["kind"]
    fam = [r for r in rows if r["scope"] == "family"]
    pool = max(0, sum(r["minutes"] for r in fam))
    good = sum(r["minutes"] for r in fam if r["eff"] == "good_day")
    good_count = sum(1 for r in fam if r["kind"] == "good_day" and not r["undone"])
    chores = sum(r["minutes"] for r in fam if r["eff"] == "chore")
    extras = sum(r["minutes"] for r in fam if r["eff"] == "adjust")
    earned = {k: 0 for k in kid_ids}
    bonus = {k: 0 for k in kid_ids}
    for r in rows:
        if r["kid"] not in earned:
            continue
        if r["scope"] == "family":
            earned[r["kid"]] += r["minutes"]
        else:
            bonus[r["kid"]] += r["minutes"]
    earned = {k: max(0, v) for k, v in earned.items()}
    family_extra = max(0, sum(r["minutes"] for r in fam if r["eff"] == "adjust" and not r["kid"]))

    naive = now.replace(tzinfo=None)
    weekday = naive.weekday()
    weekend = weekday >= 5
    base = cfg.base_minutes
    total = pool + base
    half = min(pool, 5 * -(-pool // 10))          # Saturday gets the bigger half, in 5-minute steps
    sat = cfg.base_saturday_minutes + half
    sun = cfg.base_sunday_minutes + pool - half
    today_iso = naive.date().isoformat()
    good_today = any(r["kind"] == "good_day" and not r["undone"] and r["at"][:10] == today_iso for r in rows)
    due = naive >= reminder_at(cfg, _parse(start))

    parts = [{"label": "To start (Sat + Sun)", "short": "to start", "minutes": base}]
    parts.append({"label": f"{good_count} good day{'s' if good_count != 1 else ''}", "short": "good days", "minutes": good})
    parts.append({"label": "Chores", "short": "chores", "minutes": chores})
    if extras:
        parts.append({"label": "Extra" if extras > 0 else "Taken away", "short": "extra", "minutes": extras})
    for p in parts:
        p["text"] = fmt_minutes(p["minutes"]) if p["minutes"] else "0"

    def feed_entry(r):
        k = r["kid"]
        if r["kind"] == "chore":
            title = r["note"]
        elif r["kind"] == "good_day":
            title = "A good day for everyone"
        else:
            title = r["note"] + (f" (just {names.get(k, k)})" if r["scope"] == "kid" and k else "") + \
                (f" ({names.get(k, k)})" if r["scope"] == "family" and k and r["minutes"] < 0 else "")
        return {"id": r["id"], "dow": DOW[_parse(r["at"]).weekday()], "at": r["at"], "kid": k if k in names else None,
                "title": title, "minutes": r["minutes"], "by": _first(r["by"]), "by_full": r["by"], "kind": r["kind"],
                "scope": r["scope"], "undone": r["undone"], "undo_of": r["undo_of"],
                "can_undo": r["kind"] in ("good_day", "adjust") and not r["undone"] and not r["undo_of"]}

    everything = [feed_entry(r) for r in reversed(rows)]
    # On the frame, a deduction that's just for one kid stays off the kitchen wall (it's in the parents' log).
    frame_feed = [e for e in everything if not (e["scope"] == "kid" and e["minutes"] < 0)][:6]

    return {
        "weekend": weekend,
        "day": DOW[weekday],
        "pool": pool, "base": base, "total": total, "total_label": fmt_minutes(total),
        "saturday": sat, "sunday": sun, "saturday_label": fmt_minutes(sat), "sunday_label": fmt_minutes(sun),
        "parts": parts,
        "good_days": good_count, "good_today": good_today, "good_day_minutes": cfg.good_day_minutes,
        "kid_minutes": earned, "kid_bonus": bonus, "family_extra": family_extra,
        "full": cfg.full_minutes, "pct": min(100, round(100 * total / cfg.full_minutes)) if cfg.full_minutes else 100,
        "sleeps": 0 if weekend else 5 - weekday,
        "views": list(cfg.views),
        "feed": frame_feed,
        "log": everything,
        "week_started": start, "week_started_by": marker["by"] if marker else None,
        "new_week_due": due,
        "headline": "Screen time this weekend" if weekend else "Family weekend so far",
        "note": None if weekend else f"{fmt_minutes(base)} to start, plus what everyone earns",
        "error": None,
    }


def history(db: Database, kids: list, weeks: int = 6) -> list[dict]:
    """The parents' log: recent weeks, newest first, every row with who and when."""
    names = {k.id: k.name for k in kids}
    with db.connect() as conn:
        markers = [dict(r) for r in conn.execute(
            "SELECT * FROM screen_ledger WHERE kind='new_week' ORDER BY at DESC, id DESC LIMIT ?", (weeks,)).fetchall()]
        out = []
        upper = None
        for m in markers:
            q = "SELECT * FROM screen_ledger WHERE kind != 'new_week' AND at >= ?" + (" AND at < ?" if upper else "") + \
                " ORDER BY at DESC, id DESC"
            rows = conn.execute(q, (m["at"], upper) if upper else (m["at"],)).fetchall()
            pool = max(0, sum(r["minutes"] for r in rows if r["scope"] == "family"))
            out.append({
                "started": m["at"], "started_by": m["by"], "pool": pool, "pool_label": fmt_minutes(pool),
                "rows": [{"id": r["id"], "at": r["at"], "kind": r["kind"], "minutes": r["minutes"], "scope": r["scope"],
                          "kid": r["kid"], "kid_name": names.get(r["kid"], r["kid"]), "note": r["note"], "by": r["by"],
                          "undo_of": r["undo_of"]} for r in rows],
            })
            upper = m["at"]
    return out

