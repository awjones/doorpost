"""Email updates (Settings > Email updates): short emails to parents.

- Daily chore recap, at a set time. Sent in the evening it covers today; sent before noon
  it covers yesterday. Lists chores waiting to be checked (with quick approve buttons, if
  turned on), what was approved and by whom, and what wasn't done.
- Weekend screen time, on a set day (Friday by default): Saturday and Sunday, a line per
  kid for setting limits on each device, how it added up, and a warning about chores still
  waiting. Optionally a short update Saturday morning if the total changed since.
- New week reminder: when nobody has started a new screen time week by the reminder time
  on the Screen time page.

The background loop calls tick() every minute. Each email is logged once per period (the
day or week it covers) in email_log, so a restart never sends twice; one missed while the
server was off still goes out if it's back within two hours. An email with nothing to
report is skipped.

Quick approve: each parent's daily email carries its own link secret (only its hash is
stored). The buttons open /e/<secret> and the page approves with a POST from its script,
never on a plain page load, because mail services open links on their own to scan them.
A link works for 48 hours, approves each chore once, and logs the approval as
"<name> (email)". Undo works for 10 minutes after.
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import date, datetime, timedelta
from html import escape
from typing import Optional

from . import chores as chore_logic
from . import screentime as st
from .mailer import Account, MailError, Mailer
from .timeutil import fmt_clock, fmt_minutes

log = logging.getLogger(__name__)

DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]   # Sunday first, as in Settings
PY_DAY = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
KINDS = ("daily", "weekly", "reminder")
WINDOW = timedelta(hours=2)            # a send missed while the server was off still goes out this late
REMINDER_WINDOW = timedelta(hours=24)
RETRIES = 3
RETRY_GAP = timedelta(minutes=5)
LINK_HOURS = 48
UNDO_MINUTES = 10
UPDATE_AT = "08:00"                    # the Saturday-morning update, when turned on

DEFAULTS = {
    "daily": {"on": True, "time": "19:30", "waiting": True, "approved": True, "not_done": True,
              "skip_weekend": False, "quick_approve": True},
    "weekly": {"on": True, "day": "fri", "time": "16:00", "per_kid": True, "warn_waiting": True, "update": False},
    "reminder": {"on": True},
    "people": [],
    "account": {"provider": "gmail", "host": "", "port": 587, "security": "starttls", "user": "",
                "from_name": "", "from_address": ""},
}

# colors for the emails (the Settings look's navy and gilt; email apps need literal values)
NAVY, GILT, PAPER, CARD, LINE, INK, SOFT, OK = "#16324F", "#C9A55A", "#F6F1E7", "#FFFDF8", "#E2D8C3", "#1F1B16", "#5E5547", "#2F6B37"


# ---------------- settings ----------------

def _hhmm(v, default: str) -> str:
    try:
        h, m = (int(x) for x in str(v).split(":"))
        if 0 <= h < 24 and 0 <= m < 60:
            return f"{h:02d}:{m:02d}"
    except (TypeError, ValueError):
        pass
    return default


def config(settings) -> dict:
    """Settings > Email updates with every default filled in."""
    raw = settings.email_updates or {}
    out = {}
    for k in ("daily", "weekly", "reminder", "account"):
        out[k] = {**DEFAULTS[k], **{kk: vv for kk, vv in (raw.get(k) or {}).items() if kk in DEFAULTS[k]}}
    out["daily"]["time"] = _hhmm(out["daily"]["time"], DEFAULTS["daily"]["time"])
    out["weekly"]["time"] = _hhmm(out["weekly"]["time"], DEFAULTS["weekly"]["time"])
    if out["weekly"]["day"] not in DAYS:
        out["weekly"]["day"] = DEFAULTS["weekly"]["day"]
    out["people"] = list(raw.get("people") or [])
    return out


def parent_names(settings) -> list[str]:
    names = [n for n, _h in settings.parent_pins if n]
    if not names and settings.demo and not settings.pin_hash:
        from .demo import DEMO_PINS
        names = [n for n, _p in DEMO_PINS]
    return names


def people(settings) -> list[dict]:
    """Who can get emails: every parent with a PIN (they can quick approve), then anyone else added."""
    stored = config(settings)["people"]
    out = []
    for name in parent_names(settings):
        p = next((x for x in stored if not x.get("other") and str(x.get("name", "")).lower() == name.lower()), {})
        out.append({"name": name, "email": str(p.get("email") or "").strip(), "parent": True,
                    **{k: bool(p.get(k, True)) for k in KINDS}})
    for p in stored:
        if p.get("other") and str(p.get("name") or "").strip():
            out.append({"name": str(p["name"]).strip()[:40], "email": str(p.get("email") or "").strip(), "parent": False,
                        **{k: bool(p.get(k, True)) for k in KINDS}})
    return out


def recipients(settings, kind: str) -> list[dict]:
    return [p for p in people(settings) if p["email"] and p[kind if kind in KINDS else "weekly"]]


def account(settings) -> Account:
    return Account.from_settings(config(settings)["account"], settings.smtp_password)


def app_name(settings) -> str:
    from .config import effective_config
    try:
        return str(effective_config(settings.demo).get("app_name") or "").strip()[:40] or "Doorpost"
    except Exception:  # noqa: BLE001  (an email never fails over its name)
        return "Doorpost"


# ---------------- when ----------------

def _at(day: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(day.year, day.month, day.day, h, m)


def daily_covers(cfg: dict, send_day: date) -> date:
    """Before noon the recap is about yesterday; from noon on, about today."""
    return send_day - timedelta(days=1) if cfg["daily"]["time"] < "12:00" else send_day


def due(s, now: datetime) -> list[tuple[str, str]]:
    """(kind, period) of each email whose time has come (and hasn't passed too long ago)."""
    cfg, naive = config(s.settings), now.replace(tzinfo=None)
    out = []
    d = cfg["daily"]
    if d["on"]:
        at = _at(naive.date(), d["time"])
        covers = daily_covers(cfg, naive.date())
        if at <= naive < at + WINDOW and not (d["skip_weekend"] and covers.weekday() >= 5):
            out.append(("daily", covers.isoformat()))
    w = cfg["weekly"]
    if w["on"] and PY_DAY[w["day"]] == naive.weekday():
        at = _at(naive.date(), w["time"])
        if at <= naive < at + WINDOW:
            out.append(("weekly", naive.date().isoformat()))
    if w["on"] and w["update"] and naive.weekday() == 5:
        at = _at(naive.date(), UPDATE_AT)
        if at <= naive < at + WINDOW:
            out.append(("weekly_update", naive.date().isoformat()))
    if cfg["reminder"]["on"] and s.on("screen_time"):
        start, _marker, _rows = st.week_rows(s.db)
        try:
            at = st.reminder_at(s.settings.screen_time, datetime.fromisoformat(start))
        except ValueError:
            at = None
        if at and at <= naive < at + REMINDER_WINDOW:
            out.append(("reminder", start))
    return out


def upcoming(s, now: datetime) -> list[dict]:
    """The next send of each email that is on, for Settings."""
    cfg, naive, out = config(s.settings), now.replace(tzinfo=None), []
    d = cfg["daily"]
    if d["on"]:
        for i in range(0, 8):
            day = naive.date() + timedelta(days=i)
            at = _at(day, d["time"])
            if at > naive and not (d["skip_weekend"] and daily_covers(cfg, day).weekday() >= 5):
                out.append({"kind": "daily", "at": at.isoformat(), "title": "Daily chore recap"})
                break
    w = cfg["weekly"]
    if w["on"]:
        days = (PY_DAY[w["day"]] - naive.weekday()) % 7
        at = _at(naive.date() + timedelta(days=days), w["time"])
        if at <= naive:
            at += timedelta(days=7)
        out.append({"kind": "weekly", "at": at.isoformat(), "title": "Weekend screen time"})
    if cfg["reminder"]["on"] and s.on("screen_time"):
        start, _m, _r = st.week_rows(s.db)
        try:
            at = st.reminder_at(s.settings.screen_time, datetime.fromisoformat(start))
            if at <= naive:   # due now (or overdue): the next one after a new week starts
                at = max(at, naive)
            out.append({"kind": "reminder", "at": at.isoformat(), "title": "New week reminder",
                        "note": "only if nobody has started a new week"})
        except ValueError:
            pass
    for u in out:
        u["to"] = [p["name"] for p in recipients(s.settings, u["kind"])]
    return sorted(out, key=lambda u: u["at"])


# ---------------- the log ----------------

def _row(conn, kind: str, period: str):
    return conn.execute("SELECT * FROM email_log WHERE kind=? AND period=?", (kind, period)).fetchone()


def _claim(s, kind: str, period: str, now: datetime) -> bool:
    """Take this email's slot (True), unless it's done or failed for good."""
    naive = now.replace(tzinfo=None, microsecond=0)
    with s.db.connect() as conn:
        row = _row(conn, kind, period)
        if row is None:
            conn.execute("INSERT INTO email_log (kind, period, status, at, attempts) VALUES (?, ?, 'sending', ?, 1)",
                         (kind, period, naive.isoformat()))
            return True
        if row["status"] in ("sent", "skipped") or row["attempts"] >= RETRIES:
            return False
        if naive - datetime.fromisoformat(row["at"]) < RETRY_GAP:   # failed (or cut off mid-send) a moment ago
            return False
        conn.execute("UPDATE email_log SET status='sending', at=?, attempts=attempts+1 WHERE id=?", (naive.isoformat(), row["id"]))
        return True


def _finish(s, kind: str, period: str, status: str, now: datetime, to: list[str], note: str = "", total=None) -> None:
    with s.db.connect() as conn:
        conn.execute("UPDATE email_log SET status=?, at=?, recipients=?, note=?, total=? WHERE kind=? AND period=?",
                     (status, now.replace(tzinfo=None, microsecond=0).isoformat(), ", ".join(to), note[:300], total, kind, period))


def recent(s, limit: int = 8) -> list[dict]:
    with s.db.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM email_log ORDER BY at DESC, id DESC LIMIT ?", (limit,)).fetchall()]


# ---------------- what each email says ----------------

def _kids(settings) -> dict:
    return {k.id: k for k in settings.kids}


def _approved_rows(s, day: date) -> list[dict]:
    with s.db.connect() as conn:
        rows = conn.execute("SELECT chore_id, approved_by, approved_at FROM chore_status WHERE day=? AND status='done'",
                            (day.isoformat(),)).fetchall()
    return [dict(r) for r in rows]


def daily_data(s, day: date, now: datetime) -> dict:
    kids = _kids(s.settings)
    rows = [c for c in chore_logic.chores_for(s.db, s.settings, day) if c["kid"] in kids]
    by = {r["chore_id"]: r for r in _approved_rows(s, day)}
    today = now.date()
    first = chore_logic.earliest_day(s.db, today)
    earlier = [dict(c, day_label=date.fromisoformat(c["day"]).strftime("%a"))
               for c in chore_logic.waiting_since(s.db, s.settings, first, day - timedelta(days=1)) if c["kid"] in kids] if first < day else []
    waiting = [dict(c, day=day.isoformat()) for c in rows if c["status"] == "waiting"]
    if day < first:   # too late to approve these now (a new week started)
        waiting = []
    approved = [dict(c, approved_by=st._first((by.get(c["id"]) or {}).get("approved_by") or "")) for c in rows if c["status"] == "done"]
    return {"day": day, "kids": kids, "waiting": earlier + waiting, "approved": approved,
            "todo": [c for c in rows if c["status"] == "todo"], "screen": s.screen()}


def week_data(s, now: datetime) -> dict:
    d = s.screen()
    today = now.date()
    first = chore_logic.earliest_day(s.db, today)
    kids = _kids(s.settings)
    waiting = [c for c in chore_logic.waiting_since(s.db, s.settings, first, today) if c["kid"] in kids]
    return {"screen": d, "kids": kids, "waiting": waiting, "waiting_minutes": sum(c["minutes"] for c in waiting)}


def _day_name(day: date, now: datetime) -> str:
    if day == now.date():
        return "today"
    if day == now.date() - timedelta(days=1):
        return "yesterday"
    return day.strftime("%A")


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# ---------------- HTML pieces (tables and inline styles: what email apps understand) ----------------

def _dot(kid, size: int = 26) -> str:
    color = escape(getattr(kid, "color", "#888888") or "#888888")
    initial = escape((getattr(kid, "initial", "") or getattr(kid, "name", "?")[:1]) or "?")
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;line-height:{size}px;border-radius:{size // 2}px;'
            f'background:{color};color:#FFFFFF;text-align:center;font-family:Georgia,serif;font-style:italic;font-size:{size // 2}px">{initial}</span>')


def _button(href: str, label: str, primary: bool = True) -> str:
    if primary:
        style = f"background:{NAVY};color:{GILT};border:1px solid {GILT}"
    else:
        style = f"background:#FFFFFF;color:{NAVY};border:1.5px solid {NAVY}"
    return (f'<a href="{escape(href)}" style="display:inline-block;{style};border-radius:999px;padding:10px 18px;'
            f'font-size:15px;font-weight:700;text-decoration:none;white-space:nowrap">{escape(label)}</a>')


def _cap(text: str, right: str = "") -> str:
    r = f'<td align="right" style="font-size:13px;font-weight:700;color:{OK}">{escape(right)}</td>' if right else ""
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px"><tr>'
            f'<td style="font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{SOFT};padding-bottom:6px">{escape(text)}</td>{r}</tr></table>')


def _shell(name: str, kicker: str, body: str, footer: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(name)}</title></head>
<body style="margin:0;padding:0;background:#E9E4DA">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#E9E4DA"><tr><td align="center" style="padding:20px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:{CARD};border:1px solid {LINE};border-radius:14px;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:{INK}">
<tr><td style="background:{NAVY};border-bottom:3px double {GILT};border-radius:14px 14px 0 0;padding:14px 22px">
<div style="font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:24px;color:{GILT}">{escape(name)}</div>
<div style="font-size:11px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:#B9A06E">{escape(kicker)}</div>
</td></tr>
<tr><td style="padding:20px 24px 24px">{body}</td></tr>
</table>
<p style="max-width:560px;margin:12px auto 0;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:#6E6556">{footer}</p>
</td></tr></table>
</body></html>"""


def _h1(text: str, sub: str = "") -> str:
    s = f'<p style="margin:6px 0 0;font-size:15px;line-height:1.45;color:{SOFT}">{sub}</p>' if sub else ""
    return f'<h1 style="margin:0;font-family:Georgia,\'Times New Roman\',serif;font-size:24px;font-weight:600;line-height:1.25">{escape(text)}</h1>{s}'


def _rows(cells: list[str]) -> str:
    return '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + "".join(cells) + "</table>"


# ---------------- the daily recap ----------------

def new_link(s, parent: str, items: list[list[str]], now: datetime) -> str:
    token = secrets.token_urlsafe(32)
    naive = now.replace(tzinfo=None, microsecond=0)
    with s.db.connect() as conn:
        conn.execute("INSERT INTO email_links (token_hash, parent, items, created, expires) VALUES (?, ?, ?, ?, ?)",
                     (_hash(token), parent, json.dumps(items), naive.isoformat(), (naive + timedelta(hours=LINK_HOURS)).isoformat()))
    return token


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def compose_daily(s, data: dict, now: datetime, person: Optional[dict], preview: bool = False, test: bool = False) -> Optional[dict]:
    cfg = config(s.settings)["daily"]
    waiting, approved, todo, kids = data["waiting"], data["approved"], data["todo"], data["kids"]
    if not (waiting or approved):
        return None   # nobody did anything: nothing to report
    name, base = app_name(s.settings), s.settings.frame_url
    day_word = _day_name(data["day"], now)
    weekday = data["day"].strftime("%A")
    quick = bool(cfg["quick_approve"] and waiting and base and person and person.get("parent"))
    token = ""
    if quick:
        token = "preview" if preview else new_link(s, person["name"], [[c["day"], c["id"]] for c in waiting], now)
    worth = sum(c["minutes"] for c in waiting)
    text = []
    body = []
    if waiting:
        head = f"{_plural(len(waiting), 'chore')} {'is' if len(waiting) == 1 else 'are'} waiting for you to check"
        body.append(_h1(head, f"Worth {fmt_minutes(worth)} once you approve {'it' if len(waiting) == 1 else 'them'}. You can still approve them later this week."))
        text += [head + f" (worth {fmt_minutes(worth)}).", ""]
        if quick:
            label = "Approve it" if len(waiting) == 1 else f"Approve all {len(waiting)}"
            body.append(f'<div style="margin-top:16px">{_button(f"{base}/e/{token}?all=1", label)}'
                        f'<a href="{escape(base)}/parent" style="margin-left:14px;font-size:14px;font-weight:600;color:{NAVY}">or open the parent page</a></div>')
            text += [f"{label}: {base}/e/{token}?all=1", ""]
        elif base:
            body.append(f'<div style="margin-top:16px">{_button(base + "/parent", "Check them on the parent page")}</div>')
            text += [f"Check them on the parent page: {base}/parent", ""]
        cells = []
        for i, c in enumerate(waiting if cfg["waiting"] else []):
            k = kids[c["kid"]]
            when = (f'from {c["day_label"]}' if c.get("day_label") else
                    (f'tapped “I did it” at {fmt_clock(datetime.fromisoformat(c["claimed_at"]))}' if c.get("claimed_at") else ""))
            btn = f'<td align="right" width="1%" style="padding:10px 0 10px 8px;border-top:1px solid #EEE6D6">{_button(f"{base}/e/{token}?c={i}", "Approve", primary=False)}</td>' if quick else ""
            cells.append(f'<tr><td width="34" style="padding:10px 0;border-top:1px solid #EEE6D6">{_dot(k, 30)}</td>'
                         f'<td style="padding:10px 8px;border-top:1px solid #EEE6D6;font-size:15px"><b>{escape(k.name)}</b> · {escape(c["title"])}'
                         f'<br><span style="font-size:13px;color:{SOFT}">{escape(when)}</span></td>'
                         f'<td align="right" style="padding:10px 0;border-top:1px solid #EEE6D6;font-size:13px;font-weight:700;color:{NAVY};white-space:nowrap">{c["minutes"]} min</td>{btn}</tr>')
            text.append(f"- {k.name}: {c['title']} ({c['minutes']} min){' · ' + when if when else ''}" +
                        (f"  Approve: {base}/e/{token}?c={i}" if quick else ""))
        if cells:
            body.append(_cap("Waiting to check"))
            body.append(_rows(cells))
            text.append("")
    else:
        head = f"Chores {day_word}: {_plural(len(approved), 'chore')} approved"
        body.append(_h1(head, "Nothing is waiting for you to check."))
        text += [head + ". Nothing is waiting.", ""]
    if approved and cfg["approved"]:
        mins = sum(c["minutes"] for c in approved)
        body.append(_cap(f"Approved {day_word}", f"+{fmt_minutes(mins)} to the family"))
        per: dict = {}
        for c in approved:
            per.setdefault(c["kid"], []).append(c)
        cells = []
        for kid_id, cs in per.items():
            k = kids[kid_id]
            who = sorted({c["approved_by"] for c in cs if c["approved_by"]})
            cells.append(f'<tr><td width="30" style="padding:8px 0;border-top:1px solid #EEE6D6">{_dot(k, 24)}</td>'
                         f'<td style="padding:8px;border-top:1px solid #EEE6D6;font-size:14px">{escape(k.name)} · {escape(", ".join(c["title"] for c in cs))}</td>'
                         f'<td align="right" style="padding:8px 0;border-top:1px solid #EEE6D6;font-size:14px;color:{SOFT};white-space:nowrap">'
                         f'{fmt_minutes(sum(c["minutes"] for c in cs))}{" · " + escape(", ".join(who)) if who else ""}</td></tr>')
            text.append(f"- {k.name}: {', '.join(c['title'] for c in cs)} ({fmt_minutes(sum(c['minutes'] for c in cs))})")
        body.append(_rows(cells))
        text.append("")
    if todo and cfg["not_done"]:
        body.append(_cap(f"Not done {day_word}"))
        lines = "<br>".join(f"<b>{escape(kids[c['kid']].name)}</b> · {escape(c['title'])}" for c in todo)
        body.append(f'<div style="font-size:14px;line-height:1.7;border-top:1px solid #EEE6D6;padding-top:8px">{lines}</div>')
        text += ["Not done:"] + [f"- {kids[c['kid']].name}: {c['title']}" for c in todo] + [""]
    if s.on("screen_time"):
        sc = data["screen"]
        body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;background:{PAPER};border-radius:10px">'
                    f'<tr><td style="padding:12px 14px;font-size:14px;color:{SOFT}">Family weekend so far</td>'
                    f'<td align="right" style="padding:12px 14px;font-size:15px;font-weight:700">{escape(sc["total_label"])}'
                    f'<span style="font-weight:500;color:{SOFT}"> · Sat {escape(sc["saturday_label"])} · Sun {escape(sc["sunday_label"])}</span></td></tr></table>')
        text.append(f"Family weekend so far: {sc['total_label']} (Sat {sc['saturday_label']}, Sun {sc['sunday_label']})")
    if waiting:
        subject = f"{_plural(len(waiting), 'chore')} waiting for you · {weekday}"
    else:
        subject = f"Chores {day_word}: {_plural(len(approved), 'chore')} approved · {weekday}"
    footer = ("You get this because you're on the daily chore recap. Change it in Settings › Email updates." +
              (" The Approve buttons work for 48 hours, once each, without a PIN." if quick else ""))
    return _finish_email(subject, name, f"Chores · {data['day'].strftime('%A, %B')} {data['day'].day}", body, text, footer, test)


def _finish_email(subject: str, name: str, kicker: str, body: list, text: list, footer: str, test: bool) -> dict:
    if test:
        subject = "TEST · " + subject
    html = _shell(name, kicker, "".join(body), escape(footer))
    return {"subject": subject, "html": html, "text": "\n".join(text).strip() + "\n\n" + footer + "\n"}


# ---------------- the weekend email ----------------

def kid_lines(d: dict, kids: dict) -> list[dict]:
    """A line per kid for setting each device: the family amount, plus any 'just for' extra on Saturday."""
    out = []
    for kid_id, k in kids.items():
        bonus = d["kid_bonus"].get(kid_id, 0)
        sat = d["saturday"] + bonus
        sun = d["sunday"] + min(0, sat)   # a deduction bigger than Saturday comes off Sunday too
        out.append({"kid": k, "bonus": bonus, "saturday": max(0, sat), "sunday": max(0, sun)})
    return out


def compose_weekly(s, data: dict, now: datetime, update_of: Optional[int] = None, test: bool = False) -> Optional[dict]:
    cfg = config(s.settings)["weekly"]
    d, kids = data["screen"], data["kids"]
    name, base = app_name(s.settings), s.settings.frame_url
    body, text = [], []
    title = "This weekend, for everyone"
    if update_of is not None:
        body.append(_h1("The weekend total changed", f"It was {escape(fmt_minutes(update_of))} in Friday’s email. Here’s the new split."))
        text += [f"The weekend total changed (was {fmt_minutes(update_of)}).", ""]
    body.append(_cap(title))
    tile = (lambda label, value: f'<td width="50%" style="padding:4px"><div style="background:{NAVY};border-radius:12px;padding:14px 16px">'
            f'<div style="font-size:12px;font-weight:700;letter-spacing:2px;color:{GILT}">{label}</div>'
            f'<div style="font-family:Georgia,serif;font-size:32px;font-weight:600;color:{CARD}">{escape(value)}</div></div></td>')
    body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{tile("SATURDAY", d["saturday_label"])}{tile("SUNDAY", d["sunday_label"])}</tr></table>')
    body.append(f'<p style="margin:8px 0 0;font-size:14px;color:{SOFT}">{escape(d["total_label"])} in all. Saturday gets the bigger half, same as the frame.</p>')
    text += [f"This weekend: Saturday {d['saturday_label']}, Sunday {d['sunday_label']} ({d['total_label']} in all).", ""]
    if cfg["warn_waiting"] and data["waiting"]:
        n, m = len(data["waiting"]), data["waiting_minutes"]
        new_total = fmt_minutes(d["total"] + m)
        link = f'<a href="{escape(base)}/parent" style="font-weight:700;color:{NAVY}">Check them</a>' if base else ""
        body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;background:#FBF1DC;border:1px solid #E7C98A;border-radius:12px">'
                    f'<tr><td style="padding:12px 14px;font-size:14px;line-height:1.45"><b>{_plural(n, "chore")} {"is" if n == 1 else "are"} still waiting ({fmt_minutes(m)}).</b> '
                    f'Approve {"it" if n == 1 else "them"} first and the weekend goes to {escape(new_total)}. {link}</td></tr></table>')
        text += [f"{_plural(n, 'chore')} still waiting ({fmt_minutes(m)}). Approve them first and the weekend goes to {new_total}." +
                 (f" {base}/parent" if base else ""), ""]
    if cfg["per_kid"] and kids:
        body.append(_cap("Set this on each device"))
        cells = [f'<tr><td colspan="2" style="font-size:12px;font-weight:700;color:{SOFT};padding:0 0 6px">Kid</td>'
                 f'<td align="right" style="font-size:12px;font-weight:700;color:{SOFT}">Saturday</td><td align="right" style="font-size:12px;font-weight:700;color:{SOFT}">Sunday</td></tr>']
        for line in kid_lines(d, kids):
            k, b = line["kid"], line["bonus"]
            extra = (f'<br><span style="font-size:12px;font-weight:600;color:{OK if b > 0 else "#A33A2A"}">{"+" if b > 0 else "−"}{fmt_minutes(abs(b))} just for {escape(k.name)}</span>' if b else "")
            cells.append(f'<tr><td width="30" style="padding:9px 0;border-top:1px solid #EEE6D6">{_dot(k)}</td>'
                         f'<td style="padding:9px 8px;border-top:1px solid #EEE6D6;font-size:15px">{escape(k.name)}{extra}</td>'
                         f'<td align="right" style="padding:9px 0 9px 8px;border-top:1px solid #EEE6D6;font-size:15px;font-weight:700;white-space:nowrap">{fmt_minutes(line["saturday"])}</td>'
                         f'<td align="right" style="padding:9px 0 9px 12px;border-top:1px solid #EEE6D6;font-size:15px;font-weight:700;white-space:nowrap">{fmt_minutes(line["sunday"])}</td></tr>')
            text.append(f"- {k.name}: Saturday {fmt_minutes(line['saturday'])}, Sunday {fmt_minutes(line['sunday'])}" +
                        (f" ({'+' if b > 0 else '-'}{fmt_minutes(abs(b))} just for {k.name}, on Saturday)" if b else ""))
        body.append(_rows(cells))
        if any(line["bonus"] for line in kid_lines(d, kids)):
            body.append(f'<p style="margin:6px 0 0;font-size:13px;color:#6E6556">A “just for” extra goes on Saturday here; move it to Sunday if you’d rather.</p>')
        text.append("")
    body.append(_cap("How it added up"))
    parts = [f'<tr><td style="padding:3px 0;font-size:15px">{escape(p["label"])}</td><td align="right" style="padding:3px 0;font-size:15px;font-weight:700">{escape(fmt_minutes(p["minutes"]) if p["minutes"] else "0")}</td></tr>'
             for p in d["parts"]]
    parts.append(f'<tr><td style="padding:6px 0 0;border-top:1px solid {LINE};font-size:15px;font-weight:700">Family weekend</td>'
                 f'<td align="right" style="padding:6px 0 0;border-top:1px solid {LINE};font-size:15px;font-weight:700">{escape(d["total_label"])}</td></tr>')
    body.append(_rows(parts))
    text += [f"{p['label']}: {fmt_minutes(p['minutes']) if p['minutes'] else '0'}" for p in d["parts"]] + [""]
    earned = [(kids[k], m) for k, m in d["kid_minutes"].items() if k in kids and m > 0]
    if earned:
        body.append(_cap("Who earned the chore time"))
        top = max(m for _k, m in earned)
        cells = []
        for k, m in sorted(earned, key=lambda x: -x[1]):
            width = max(6, round(220 * m / top))
            cells.append(f'<tr><td width="90" style="padding:3px 0;font-size:14px">{escape(k.name)}</td>'
                         f'<td style="padding:3px 0"><div style="height:12px;width:{width}px;background:{escape(k.color)};border-radius:6px"></div></td>'
                         f'<td align="right" style="padding:3px 0;font-size:14px;font-weight:700;white-space:nowrap">{fmt_minutes(m)}</td></tr>')
        body.append(_rows(cells))
    if base:
        body.append(f'<div style="margin-top:20px">{_button(base + "/parent", "Open screen time")}</div>')
    subject = (f"Weekend screen time update: Sat {d['saturday_label']}, Sun {d['sunday_label']}" if update_of is not None
               else f"Weekend screen time: Sat {d['saturday_label']}, Sun {d['sunday_label']}")
    footer = "The week keeps counting until a parent taps Start a new week. Change this email in Settings › Email updates."
    start = _week_begins(s, now)
    return _finish_email(subject, name, f"Screen time · Week of {start.strftime('%B')} {start.day}", body, text, footer, test)


def _week_begins(s, now: datetime) -> date:
    """The day this screen time week started (a Sunday-evening start is that Sunday), for headings."""
    start, _m, _r = st.week_rows(s.db)
    try:
        return datetime.fromisoformat(start).date() if not start.startswith("2000") else now.date()
    except ValueError:
        return now.date()


# ---------------- the new week reminder ----------------

def compose_reminder(s, now: datetime, test: bool = False) -> Optional[dict]:
    d = s.screen()
    if not d.get("new_week_due") and not test:
        return None
    name, base = app_name(s.settings), s.settings.frame_url
    cfg = s.settings.screen_time
    start, _m, rows = st.week_rows(s.db)
    chores = sum(1 for r in rows if r["kind"] == "chore" and not r["undone"])
    body = [_h1("Nobody has started a new week yet",
                f"Last week finished at <b style=\"color:{INK}\">{escape(d['total_label'])}</b> for the family. Starting a new week sets the earned time back to zero. "
                f"The {escape(fmt_minutes(cfg.base_minutes))} to start next weekend stays.")]
    body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;background:{PAPER};border-radius:10px">'
                f'<tr><td style="padding:10px 14px 2px;font-size:14px">Chores approved</td><td align="right" style="padding:10px 14px 2px;font-size:14px;font-weight:700">{chores}</td></tr>'
                f'<tr><td style="padding:2px 14px 10px;font-size:14px">Good days</td><td align="right" style="padding:2px 14px 10px;font-size:14px;font-weight:700">{d["good_days"]}</td></tr></table>')
    if base:
        body.append(f'<div style="margin-top:18px">{_button(base + "/parent", "Start a new week on the parent page")}</div>')
    text = [f"Nobody has started a new screen time week yet. Last week finished at {d['total_label']}.",
            f"Chores approved: {chores}. Good days: {d['good_days']}.", (f"Start a new week: {base}/parent" if base else "")]
    footer = "Sent only when the week hasn't been started by the time set on the Screen time page. Nothing resets by itself."
    return _finish_email("Start a new screen time week?", name, f"Screen time · {now.strftime('%A, %B')} {now.day}", body, text, footer, test)


# ---------------- sending ----------------

def make_mailer(settings, data_dir) -> Mailer:
    return Mailer(settings.demo, data_dir / "outbox-demo")


def _send_each(s, people_: list[dict], build) -> tuple[list[str], list[str]]:
    """Build and send one email per person (each daily email has its own links). Returns (sent to, errors)."""
    acct, name = account(s.settings), app_name(s.settings)
    sent, errors = [], []
    for p in people_:
        msg = build(p)
        if msg is None:
            continue
        try:
            s.mailer.send(acct, p["email"], msg["subject"], msg["text"], msg["html"], name)
            sent.append(p["name"])
        except MailError as exc:
            errors.append(f"{p['name']}: {exc}")
        except Exception as exc:  # noqa: BLE001  (one bad send never stops the loop)
            log.exception("email to %s failed", p["name"])
            errors.append(f"{p['name']}: {exc}")
    return sent, errors


def run(s, kind: str, period: str, now: datetime) -> str:
    """Send one scheduled email (already claimed). Returns its status."""
    to = recipients(s.settings, "weekly" if kind == "weekly_update" else kind)
    if not to:
        _finish(s, kind, period, "skipped", now, [], "Nobody gets this email (Settings > Email updates).")
        return "skipped"
    total = None
    if kind == "daily":
        data = daily_data(s, date.fromisoformat(period), now)
        if compose_daily(s, data, now, None, preview=True) is None:
            _finish(s, kind, period, "skipped", now, [], "Nothing to report.")
            return "skipped"
        build = lambda p: compose_daily(s, data, now, p)
    elif kind in ("weekly", "weekly_update"):
        data = week_data(s, now)
        total = data["screen"]["total"]
        update_of = None
        if kind == "weekly_update":
            with s.db.connect() as conn:
                last = conn.execute("SELECT total FROM email_log WHERE kind='weekly' AND status='sent' AND period >= ? ORDER BY period DESC LIMIT 1",
                                    ((now.date() - timedelta(days=6)).isoformat(),)).fetchone()
            if not last or last["total"] is None or last["total"] == total:
                _finish(s, kind, period, "skipped", now, [], "The total didn't change.", total)
                return "skipped"
            update_of = last["total"]
        build = lambda p: compose_weekly(s, data, now, update_of)
    elif kind == "reminder":
        if compose_reminder(s, now) is None:
            _finish(s, kind, period, "skipped", now, [], "A new week was already started.")
            return "skipped"
        build = lambda p: compose_reminder(s, now)
    else:
        return "skipped"
    sent, errors = _send_each(s, to, build)
    status = "sent" if sent and not errors else ("failed" if errors else "skipped")
    _finish(s, kind, period, status, now, sent, "; ".join(errors), total)
    return status


def tick(s, now: Optional[datetime] = None) -> list[tuple[str, str, str]]:
    """Called every minute by the background loop: send whatever is due."""
    now = now or s.now()
    if not s.on("email_updates") or not s.on("chores"):
        return []
    if not s.settings.demo and not account(s.settings).ready:
        return []   # nothing can go out yet; the log stays empty so it starts cleanly once set up
    done = []
    for kind, period in due(s, now):
        if _claim(s, kind, period, now):
            try:
                done.append((kind, period, run(s, kind, period, now)))
            except Exception as exc:  # noqa: BLE001
                log.exception("email update %s failed", kind)
                _finish(s, kind, period, "failed", now, [], str(exc))
    return done


def send_test(s, kind: str, person: dict, now: datetime) -> dict:
    """Settings' "Send a test": today's real numbers, to one person, marked TEST."""
    if kind == "daily":
        day = daily_covers(config(s.settings), now.date())
        msg = compose_daily(s, daily_data(s, day, now), now, person, test=True)
        if msg is None and s.settings.kids:   # nothing yet today: one sample line, so the test shows the layout
            msg = compose_daily(s, {**daily_data(s, day, now), "approved": [{"kid": s.settings.kids[0].id, "title": "(sample line: nothing approved yet)",
                                                                             "minutes": 0, "approved_by": ""}]},
                                now, person, test=True)
    elif kind == "weekly":
        msg = compose_weekly(s, week_data(s, now), now, test=True)
    elif kind == "reminder":
        msg = compose_reminder(s, now, test=True)
    else:
        raise ValueError("Pick the daily, weekly or reminder email.")
    if msg is None:
        raise ValueError("Nothing to put in that email yet.")
    s.mailer.send(account(s.settings), person["email"], msg["subject"], msg["text"], msg["html"], app_name(s.settings))
    stamp = now.replace(tzinfo=None, microsecond=0).isoformat()
    with s.db.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO email_log (kind, period, status, at, recipients, note, attempts) VALUES ('test', ?, 'sent', ?, ?, ?, 1)",
                     (stamp, stamp, person["name"], f"Test of the {kind} email"))
    return {"subject": msg["subject"], "to": person["email"]}


def preview(s, kind: str, now: datetime) -> str:
    """The email as HTML, for Settings' Preview (quick approve buttons are shown but do nothing)."""
    person = next((p for p in people(s.settings) if p["parent"]), {"name": "Parent", "parent": True, "email": ""})
    if kind == "daily":
        msg = compose_daily(s, daily_data(s, daily_covers(config(s.settings), now.date()), now), now, person, preview=True)
    elif kind == "weekly":
        msg = compose_weekly(s, week_data(s, now), now)
    else:
        msg = compose_reminder(s, now, test=True)
    if msg is None:
        return _shell(app_name(s.settings), "Preview", _h1("Nothing to report yet", "This email is skipped on a day nobody marked or approved a chore."), "")
    return msg["html"]


# ---------------- quick approve links ----------------

class LinkError(Exception):
    pass


def _link(s, token: str):
    if not token or len(token) > 100:
        return None
    with s.db.connect() as conn:
        return conn.execute("SELECT * FROM email_links WHERE token_hash=?", (_hash(token),)).fetchone()


def _uses(s, token_hash: str) -> dict:
    with s.db.connect() as conn:
        rows = conn.execute("SELECT * FROM email_link_uses WHERE token_hash=? ORDER BY id", (token_hash,)).fetchall()
    return {r["idx"]: dict(r) for r in rows}   # the latest use of each item


def link_view(s, token: str, now: Optional[datetime] = None) -> dict:
    now = now or s.now()
    row = _link(s, token)
    if row is None:
        return {"state": "unknown"}
    naive = now.replace(tzinfo=None)
    kids = _kids(s.settings)
    uses = _uses(s, row["token_hash"])
    items = []
    with s.db.connect() as conn:
        for i, (day, cid) in enumerate(json.loads(row["items"])):
            c = next((c for c in s.settings.chores if c.id == cid), None)
            if c is None or c.kid not in kids:
                continue
            r = conn.execute("SELECT * FROM chore_status WHERE day=? AND chore_id=?", (day, cid)).fetchone()
            status = r["status"] if r else "todo"
            use = uses.get(i)
            can_undo = bool(use and not use["undone_at"] and status == "done"
                            and naive - datetime.fromisoformat(use["approved_at"]) < timedelta(minutes=UNDO_MINUTES))
            k = kids[c.kid]
            items.append({"idx": i, "kid": k.name, "initial": k.initial, "color": k.color, "title": c.title,
                          "minutes": c.minutes, "day": day, "day_label": date.fromisoformat(day).strftime("%A"),
                          "status": status, "approved_by": st._first(r["approved_by"]) if r and r["approved_by"] else "",
                          "can_undo": can_undo})
    expired = naive >= datetime.fromisoformat(row["expires"])
    sc = s.screen() if s.on("screen_time") else None
    return {"state": "expired" if expired else "ready", "parent": row["parent"], "items": items,
            "total_label": sc["total_label"] if sc else None, "app_name": app_name(s.settings)}


def link_approve(s, token: str, idxs: list[int], now: Optional[datetime] = None) -> dict:
    now = now or s.now()
    row = _link(s, token)
    if row is None:
        raise LinkError("This link isn't valid.")
    if now.replace(tzinfo=None) >= datetime.fromisoformat(row["expires"]):
        raise LinkError("This link has expired. Approve on the parent page instead.")
    items = json.loads(row["items"])
    by = f"{row['parent']} (email)"
    approved, skipped = [], []
    for i in idxs:
        if not 0 <= i < len(items):
            continue
        day, cid = items[i]
        try:
            approved.append(chore_logic.approve_on(s.db, s.settings, cid, date.fromisoformat(day), now, by))
        except chore_logic.ChoreError as exc:
            skipped.append(str(exc))
            continue
        with s.db.connect() as conn:
            conn.execute("INSERT INTO email_link_uses (token_hash, idx, approved_at) VALUES (?, ?, ?)",
                         (row["token_hash"], i, now.replace(tzinfo=None, microsecond=0).isoformat()))
    return {"approved": approved, "skipped": skipped, **link_view(s, token, now)}


def link_undo(s, token: str, idx: int, now: Optional[datetime] = None) -> dict:
    now = now or s.now()
    view = link_view(s, token, now)
    item = next((x for x in view.get("items", []) if x["idx"] == idx), None)
    if view["state"] == "unknown" or item is None:
        raise LinkError("This link isn't valid.")
    if not item["can_undo"]:
        raise LinkError("This can't be undone from here any more. Use the parent page.")
    row = _link(s, token)
    day, cid = json.loads(row["items"])[idx]
    chore_logic.unapprove(s.db, s.settings, cid, date.fromisoformat(day), now, f"{row['parent']} (email)")
    with s.db.connect() as conn:
        conn.execute("UPDATE email_link_uses SET undone_at=? WHERE token_hash=? AND idx=? AND undone_at IS NULL",
                     (now.replace(tzinfo=None, microsecond=0).isoformat(), row["token_hash"], idx))
    return link_view(s, token, now)
