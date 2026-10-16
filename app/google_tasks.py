"""Google Tasks as a source for the frame's lists (the other source is Apple Reminders through a Mac).

Google Tasks has a web API, so no extra computer is needed: the server signs in once (Settings > Lists >
Connect Google, shared with the Photos Picker, see app/google_auth.py) and every minute:
1. sends what was added or checked off on the frame (Lists.changes("google")),
2. reads the names of all task lists, and the tasks on the lists shown on the frame,
3. hands both to Lists.sync(..., source="google"), the same path the Mac's Reminders check-in uses.

List ids on the frame are "gtasks:<Google task list id>", item ids "g:<Google task id>".
Checked-off tasks stay on the frame's "Done today" for two days, like Reminders.
"""
from __future__ import annotations

import logging
import secrets
import threading
from datetime import datetime, timedelta
from typing import Optional

from .google_auth import GoogleAccount, GoogleError
from .lists import GOOGLE_PREFIX, Lists

log = logging.getLogger(__name__)

API = "https://tasks.googleapis.com/tasks/v1"
KEEP_DONE = timedelta(days=2)
_LOCK = threading.Lock()   # the minute loop and a tap on the frame never sync at the same time


class GoogleTasks:
    """A thin client for the parts of the Google Tasks API the frame uses."""

    def __init__(self, account: GoogleAccount):
        self.account = account

    def _call(self, method: str, path: str, **kw) -> dict:
        return self.account.call(method, API + path, what="Google Tasks", **kw)

    def tasklists(self) -> list[dict]:
        out, page = [], None
        while True:
            params = {"maxResults": 100, **({"pageToken": page} if page else {})}
            r = self._call("GET", "/users/@me/lists", params=params)
            out += r.get("items", [])
            page = r.get("nextPageToken")
            if not page:
                return out

    def tasks(self, tasklist: str) -> list[dict]:
        """Every task on a list, open and checked off (showHidden: tasks checked off in Google's apps are 'hidden')."""
        out, page = [], None
        while True:
            params = {"maxResults": 100, "showCompleted": "true", "showHidden": "true", **({"pageToken": page} if page else {})}
            r = self._call("GET", f"/lists/{tasklist}/tasks", params=params)
            out += [t for t in r.get("items", []) if not t.get("deleted")]
            page = r.get("nextPageToken")
            if not page:
                return out

    def insert(self, tasklist: str, title: str, notes: str = "", done: bool = False) -> dict:
        body = {"title": title, "notes": notes, "status": "completed" if done else "needsAction"}
        return self._call("POST", f"/lists/{tasklist}/tasks", json=body)

    def set_done(self, tasklist: str, task_id: str, done: bool) -> dict:
        body = {"status": "completed"} if done else {"status": "needsAction", "completed": None}
        return self._call("PATCH", f"/lists/{tasklist}/tasks/{task_id}", json=body)


def _parse(v: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")) if v else None
    except ValueError:
        return None


def _push(lists: Lists, api: GoogleTasks) -> list[dict]:
    """Send the frame's changes to Google. Returns the 'applied' records Lists.sync expects.
    A change that failed for a passing reason (network, Google busy) is left for the next minute."""
    applied = []
    for ch in lists.changes("google"):
        try:
            if ch["op"] == "add":
                t = api.insert(ch["list"][len(GOOGLE_PREFIX):], ch["title"], ch.get("notes") or "", ch.get("done", False))
                applied.append({"local": ch["local"], "ok": True, "ext": t["id"]})
            else:
                lid = lists.list_of(ch["local"]) or ""
                api.set_done(lid[len(GOOGLE_PREFIX):], ch["ext"], ch["done"])
                applied.append({"local": ch["local"], "ok": True})
        except GoogleError as exc:
            if exc.status in (400, 404, 410):    # the list or task is gone at Google: drop the change
                applied.append({"local": ch["local"], "ok": False})
            elif exc.status in (401, 403):
                raise
            else:
                log.info("Google Tasks change waits for the next try: %s", exc)
    return applied


def sync(lists: Lists, api: GoogleTasks, now: datetime) -> dict:
    """One round with Google: push the frame's changes, then read what's there now."""
    with _LOCK:
        applied = _push(lists, api)
        if applied:   # record them now, so a failed read below can't send the same new item twice
            lists.sync({"applied": applied}, now, source="google")
        all_lists = api.tasklists()
        shown = {x for x in lists.shown() if x.startswith(GOOGLE_PREFIX)}
        body_lists, items = [], {}
        for tl in all_lists:
            lid = GOOGLE_PREFIX + tl["id"]
            if lid in shown:
                rows = []
                tasks = sorted(api.tasks(tl["id"]), key=lambda t: (t.get("parent") or "", t.get("position") or ""))
                for i, t in enumerate(tasks):
                    title = (t.get("title") or "").strip()
                    done = t.get("status") == "completed"
                    done_at = _parse(t.get("completed"))
                    if not title or (done and done_at and now - done_at > KEEP_DONE):
                        continue
                    rows.append({"ext": t["id"], "title": title, "notes": t.get("notes") or "", "done": done,
                                 "done_at": t.get("completed"), "modified": t.get("updated"),
                                 # Google has no "created" time: new tasks keep Google's order, the first time they're seen.
                                 "created": (now + timedelta(milliseconds=i)).isoformat()})
                items[lid] = rows
                count = sum(1 for r in rows if not r["done"])
            else:
                count = 0
            body_lists.append({"id": lid, "name": tl.get("title") or "Tasks", "count": count})
        lists.sync({"lists": body_lists, "items": items}, now, source="google")
        lists.set_error("google", None)
        return {"lists": len(body_lists), "shown": len(items)}


def demo_sync(lists: Lists, now: datetime) -> None:
    """Demo mode: no Google account. Pretend Google took every change, so nothing waits forever."""
    with _LOCK:
        applied = [{"local": c["local"], "ok": True, **({"ext": "demo-" + secrets.token_hex(4)} if c["op"] == "add" else {})}
                   for c in lists.changes("google")]
        lists.sync({"applied": applied}, now, source="google")


def sync_now(services) -> None:
    """Called every minute by the server (and after a change on the frame). Quiet unless Google Tasks is set up."""
    L = services.lists
    if not L.google_on:
        return
    if services.settings.demo:
        demo_sync(L, services.now())
        return
    acct = services.google()
    if not (acct.configured and acct.has("tasks")):
        return
    try:
        sync(L, GoogleTasks(acct), services.now())
    except GoogleError as exc:
        log.warning("Google Tasks: %s", exc)
        L.set_error("google", str(exc))


DEMO_LISTS = [
    {"id": GOOGLE_PREFIX + "demo-projects", "name": "Weekend projects", "count": 3},
    {"id": GOOGLE_PREFIX + "demo-school", "name": "School supplies", "count": 4},
    {"id": GOOGLE_PREFIX + "demo-gifts", "name": "Gift ideas (Mom)", "count": 7},
]


def seed_demo(lists: Lists, now: datetime) -> None:
    """Sample Google Tasks lists, so Settings > Lists shows both sources in demo mode."""
    if any(a["source"] == "google" for a in lists.available()):
        return
    projects = [{"ext": f"p{i}", "title": t, "notes": "", "done": False, "created": (now - timedelta(days=2, minutes=-i)).isoformat()}
                for i, t in enumerate(["Rake the leaves", "Fix the porch light", "Clean out the garage"])]
    school = [{"ext": f"s{i}", "title": t, "notes": "", "done": False, "created": (now - timedelta(days=1, minutes=-i)).isoformat()}
              for i, t in enumerate(["Glue sticks", "Poster board", "Colored pencils", "Folders (3)"])]
    lists.sync({"lists": DEMO_LISTS, "items": {DEMO_LISTS[0]["id"]: projects, DEMO_LISTS[1]["id"]: school}},
               now - timedelta(seconds=25), source="google")
