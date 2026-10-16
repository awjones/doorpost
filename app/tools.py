"""Small admin commands.

    python -m app.tools set-pin        # a shared parent PIN, writes FRAME_PIN_HASH to .env (one each: use Settings)
    python -m app.tools new-secret     # writes a random FRAME_SECRET to .env
    python -m app.tools check          # loads config and tries every data source once
"""
from __future__ import annotations

import getpass
import secrets
import sys

from .auth import hash_pin
from .config import ROOT

ENV = ROOT / ".env"


def _set_env(key: str, value: str) -> None:
    lines = ENV.read_text().splitlines() if ENV.exists() else []
    lines = [ln for ln in lines if not ln.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    ENV.write_text("\n".join(lines) + "\n")
    ENV.chmod(0o600)


def set_pin() -> None:
    pin = getpass.getpass("New parent PIN (4-8 digits): ")
    if pin != getpass.getpass("Type it again: "):
        sys.exit("PINs didn't match.")
    _set_env("FRAME_PIN_HASH", hash_pin(pin))
    print("Saved. Restart the service to use the new PIN.")


def new_secret() -> None:
    _set_env("FRAME_SECRET", secrets.token_urlsafe(32))
    print("Saved a new FRAME_SECRET (signs parent phone sessions). Restart the service.")


def check() -> None:
    from datetime import timedelta

    from .calendar_feed import CalendarService
    from .config import DATA_DIR, load_settings
    from .db import Database
    from .screentime import summary
    from .timeutil import now_in
    from .weather import WeatherService

    s = load_settings()
    now = now_in(s.timezone)
    print(f"Timezone {s.timezone}, now {now:%a %b %d %H:%M}, demo={s.demo}")
    print(f"Kids: {', '.join(k.name for k in s.kids)}; {len(s.chores)} chores configured")
    cal = CalendarService(s, DATA_DIR / "calendar-cache")
    cal.refresh()
    for c in s.calendars:
        state = "ERROR " + cal.errors[c.key] if c.key in cal.errors else "ok"
        print(f"  calendar {c.key:8s} {state}")
    evs = cal.events_between(now.date(), now.date() + timedelta(days=7))
    print(f"  {len(evs)} events in the next 7 days")
    ws = WeatherService.from_settings(s)
    w = ws.get(now)
    print(f"Weather ({ws.label() or ws.source()}): {w or 'ERROR ' + str(ws.error)}")
    sc = summary(Database(DATA_DIR / ("demo.db" if s.demo else "frame.db")), s.screen_time, s.kids, now)
    print(f"Screen time: {sc['total_label']} ({sc['headline'].lower()}); new week due: {sc['new_week_due']}")
    print(f"Parent PINs: {', '.join(n for n, _ in s.parent_pins) or 'none'}; shared PIN set: {bool(s.pin_hash)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"set-pin": set_pin, "new-secret": new_secret, "check": check}.get(
        cmd, lambda: sys.exit(__doc__))()
