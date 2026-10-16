"""Lists from Apple Reminders or Google Tasks: Groceries first, and any other list can be turned on in Settings > Lists.

Each list has a source, kept with it:
- "apple": Apple has no web service for Reminders, so a small helper on the Mac
  (mac/lists-helper, see docs/lists.md) posts the chosen lists to /api/lists/sync
  every 30 seconds and picks up what was added or checked off on the frame.
- "google": the server itself reads Google Tasks every minute (app/google_tasks.py).
  Those lists have ids starting with "gtasks:".
Changes made on the frame wait in `pending` until the source has them; if the same
item changed at the source after that, the newer change wins.
"""
from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from .db import Database

SCHEMA = """
CREATE TABLE IF NOT EXISTS list_items (
    id         TEXT PRIMARY KEY,      -- 'r:<Reminders id>', 'g:<Google task id>', or 'f:<random>' for an item added on the frame not there yet
    list       TEXT NOT NULL,         -- the list's id (Reminders id, or 'gtasks:<Google task list id>')
    ext        TEXT,                  -- the item's id in Reminders or Google Tasks
    title      TEXT NOT NULL,
    notes      TEXT NOT NULL DEFAULT '',
    done       INTEGER NOT NULL DEFAULT 0,
    done_at    TEXT,                  -- ISO time it was checked off
    created    TEXT,
    modified   TEXT,                  -- last change in Reminders (ISO)
    from_frame INTEGER NOT NULL DEFAULT 0,
    pending    TEXT,                  -- 'add', 'done' or 'undone' until the Mac has written it to Reminders
    pending_at TEXT
);
CREATE INDEX IF NOT EXISTS list_items_list ON list_items(list);
-- Everything that has been on a list, for the "Bought before" suggestions when adding.
CREATE TABLE IF NOT EXISTS list_history (
    list  TEXT NOT NULL,
    key   TEXT NOT NULL,
    title TEXT NOT NULL,
    n     INTEGER NOT NULL DEFAULT 1,
    last  TEXT NOT NULL,
    PRIMARY KEY (list, key)
);
CREATE TABLE IF NOT EXISTS list_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

FRAME_NOTE = "Added on the frame"
SOURCES = {"apple": "Apple Reminders", "google": "Google Tasks"}
ITEM_PREFIX = {"apple": "r:", "google": "g:"}
GOOGLE_PREFIX = "gtasks:"   # Google Tasks list ids on the frame

# "Groceries look": items sorted into store sections by a word in their name.
SECTIONS = [
    ("Produce", "apple banana berr strawberr blueberr raspberr grape orange lemon lime avocado lettuce spinach kale salad tomato "
                "potato onion garlic carrot celery cucumber pepper broccoli cauliflower corn mushroom zucchini squash pumpkin pear "
                "peach plum melon watermelon cantaloupe pineapple mango cilantro parsley basil herb ginger cabbage green bean asparagus fruit veg"),
    ("Meat & seafood", "chicken beef steak pork bacon sausage ham turkey ground hamburger hot dog fish salmon tuna shrimp meat brisket ribs"),
    ("Dairy & eggs", "milk egg cheese cheddar mozzarella parmesan butter yogurt cream sour cream half and half cottage creamer"),
    ("Bakery", "bread bagel bun roll tortilla muffin croissant english muffin pita loaf"),
    ("Frozen", "frozen ice cream pizza waffle popsicle fries tater"),
    ("Pantry", "rice pasta noodle spaghetti flour sugar salt oil vinegar sauce ketchup mustard mayo peanut butter jelly jam honey syrup "
               "cereal oat oatmeal bean soup broth stock spice seasoning baking sauce coffee tea"),
    ("Snacks", "chip cracker cookie pretzel popcorn granola bar candy chocolate goldfish snack nuts"),
    ("Drinks", "juice soda water sparkling lemonade gatorade drink"),
    ("Household", "paper towel toilet paper tissue napkin trash bag foil wrap ziploc detergent soap dish sponge cleaner bleach battery bulb filter"),
    ("Personal care", "shampoo conditioner toothpaste toothbrush deodorant lotion razor floss vitamin medicine bandaid band-aid sunscreen"),
    ("Baby & kids", "diaper wipe formula baby"),
]
_SECTION_WORDS = [(name, words.split()) for name, words in SECTIONS]
PHRASES = {"peanut butter": "Pantry", "almond butter": "Pantry", "ice cream": "Frozen", "sour cream": "Dairy & eggs",
           "cream cheese": "Dairy & eggs", "half and half": "Dairy & eggs", "hot dog": "Meat & seafood", "paper towel": "Household",
           "toilet paper": "Household", "green bean": "Produce", "english muffin": "Bakery", "baby wipe": "Baby & kids",
           "baby food": "Baby & kids", "trash bag": "Household", "dish soap": "Household", "hand soap": "Household"}


def section_for(title: str) -> str:
    """The store section for a grocery item. The last word usually names the thing ("baby spinach", "sandwich bread")."""
    t = " ".join(re.sub(r"[^a-z ]", " ", title.lower()).split())
    for phrase, name in PHRASES.items():
        if phrase in t:
            return name
    best = "Other"
    for word in t.split():
        for name, stems in _SECTION_WORDS:
            if any(word.startswith(stem) for stem in stems):
                best = name
                break
    return best


def _key(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def _ago(then: datetime, now: datetime) -> str:
    s = int((now - then).total_seconds())
    if s < 90:
        return f"{max(s, 1)} seconds ago" if s >= 5 else "just now"
    if s < 3600:
        m = s // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if s < 86400 * 2:
        h = s // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    return f"{s // 86400} days ago"


def _time_label(dt: datetime, now: datetime) -> str:
    t = dt.strftime("%I:%M %p").lstrip("0")
    return t if dt.date() == now.date() else "yesterday · " + t if dt.date() == now.date() - timedelta(days=1) else dt.strftime("%b %d")


class Lists:
    def __init__(self, db: Database, cfg: Optional[dict] = None):
        self.db = db
        self.cfg = dict(cfg or {})
        with db.connect() as conn:
            conn.executescript(SCHEMA)

    # ---------- settings (store key "lists", edited in Settings > Lists) ----------
    def _meta(self, key: str, default=None):
        with self.db.connect() as conn:
            row = conn.execute("SELECT value FROM list_meta WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def _set_meta(self, conn, key: str, value) -> None:
        conn.execute("INSERT INTO list_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                     (key, json.dumps(value)))

    def available(self) -> list[dict]:
        """Every list the sources reported: [{id, name, count, source}]."""
        return [dict(a, source=a.get("source") or "apple") for a in self._meta("available", [])]

    def source_of(self, list_id: Optional[str]) -> Optional[str]:
        if not list_id:
            return None
        if list_id.startswith(GOOGLE_PREFIX):
            return "google"
        return next((a["source"] for a in self.available() if a["id"] == list_id), "apple")

    def list_of(self, item_id: str) -> Optional[str]:
        with self.db.connect() as conn:
            r = conn.execute("SELECT list FROM list_items WHERE id = ?", (item_id,)).fetchone()
        return r["list"] if r else None

    @property
    def google_on(self) -> bool:
        """Settings > Lists > Use Google Tasks (on unless turned off; nothing happens until Google is connected)."""
        return bool(self.cfg.get("google", True))

    def shown(self) -> list[str]:
        """The lists on the frame. Until Settings picks some, any list called Groceries (or Grocery)."""
        off = (lambda x: x.startswith(GOOGLE_PREFIX)) if not self.google_on else (lambda x: False)
        if "shown" in self.cfg:
            return [x for x in self.cfg["shown"] if not off(x)]
        return [a["id"] for a in self.available() if not off(a["id"]) and _key(a["name"]) in ("groceries", "grocery", "grocery list")]

    def home(self) -> Optional[str]:
        shown = self.shown()
        h = self.cfg.get("home")
        return h if h in shown else (shown[0] if shown else None)

    def sections_on(self, list_id: str) -> bool:
        if "sections" in self.cfg:
            return list_id in self.cfg["sections"]
        name = next((a["name"] for a in self.available() if a["id"] == list_id), "")
        return "grocer" in name.lower()

    @property
    def can_add(self) -> bool:
        return bool(self.cfg.get("anyone_add", True))

    @property
    def can_check(self) -> bool:
        return bool(self.cfg.get("anyone_check", True))

    @staticmethod
    def _synced_key(source: str) -> str:
        return "synced_at" if source == "apple" else f"synced_at:{source}"

    def synced_at(self, source: str = "apple") -> Optional[datetime]:
        v = self._meta(self._synced_key(source))
        return datetime.fromisoformat(v) if v else None

    def error(self, source: str) -> Optional[str]:
        return self._meta(f"error:{source}")

    def set_error(self, source: str, message: Optional[str]) -> None:
        with self.db.connect() as conn:
            if message:
                self._set_meta(conn, f"error:{source}", message[:300])
            else:
                conn.execute("DELETE FROM list_meta WHERE key = ?", (f"error:{source}",))

    # ---------- what the frame shows ----------
    def _local(self, iso: Optional[str], now: datetime) -> Optional[datetime]:
        if not iso:
            return None
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(now.tzinfo).replace(tzinfo=None) if dt.tzinfo and now.tzinfo else dt.replace(tzinfo=None)

    def frame_view(self, now: datetime) -> dict:
        names = {a["id"]: a["name"] for a in self.available()}
        today = now.date()
        naive_now = now.replace(tzinfo=None)
        sync_info = {}
        for src in SOURCES:
            at = self.synced_at(src)
            # The Mac checks in every 30 s and the server reads Google every minute; after 10 minutes say so.
            sync_info[src] = {"synced": _ago(at, naive_now) if at else None,
                              "stale": bool(at is None or (naive_now - at) > timedelta(minutes=10))}
        out = []
        with self.db.connect() as conn:
            for lid in self.shown():
                rows = conn.execute("SELECT * FROM list_items WHERE list = ? ORDER BY created, id", (lid,)).fetchall()
                hist = conn.execute("SELECT title FROM list_history WHERE list = ? ORDER BY n DESC, last DESC LIMIT 60", (lid,)).fetchall()
                sections = self.sections_on(lid)
                items, done = [], []
                for r in rows:
                    item = {"id": r["id"], "title": r["title"], "notes": r["notes"], "frame": bool(r["from_frame"]),
                            "waiting": bool(r["pending"])}
                    if r["done"]:
                        at = self._local(r["done_at"], now)
                        if at and at.date() == today:
                            item["when"] = _time_label(at, naive_now)
                            done.append((r["done_at"] or "", item))
                    else:
                        if sections:
                            item["section"] = section_for(r["title"])
                        items.append(item)
                if sections:
                    order = [s[0] for s in SECTIONS] + ["Other"]
                    items.sort(key=lambda i: order.index(i["section"]))
                done.sort(key=lambda x: x[0], reverse=True)
                src = self.source_of(lid)
                out.append({"id": lid, "name": names.get(lid, "List"), "sections": sections, "open": len(items),
                            "items": items, "done": [d[1] for d in done], "bought": [h["title"] for h in hist],
                            "source": src, "from": SOURCES[src], **sync_info[src]})
        # Overall: the source of the list on the Today screen (Apple when nothing is shown, as before).
        main = self.source_of(self.home()) or "apple"
        return {"lists": out, "home": self.home(), "can_add": self.can_add, "can_check": self.can_check, **sync_info[main]}

    # ---------- changes made on the frame ----------
    def _remember(self, conn, list_id: str, title: str, now: datetime) -> None:
        conn.execute("INSERT INTO list_history (list, key, title, n, last) VALUES (?, ?, ?, 1, ?) "
                     "ON CONFLICT(list, key) DO UPDATE SET n = n + 1, last = excluded.last, title = excluded.title",
                     (list_id, _key(title), title.strip(), now.isoformat()))

    def add(self, list_id: str, title: str, now: datetime) -> dict:
        title = re.sub(r"\s+", " ", title).strip()[:120]
        if not title:
            raise ValueError("Type what to add.")
        if list_id not in self.shown():
            raise KeyError(list_id)
        iid = "f:" + secrets.token_hex(6)
        stamp = now.isoformat()
        with self.db.connect() as conn:
            conn.execute("INSERT INTO list_items (id, list, title, notes, created, modified, from_frame, pending, pending_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, 1, 'add', ?)", (iid, list_id, title, FRAME_NOTE, stamp, stamp, stamp))
            self._remember(conn, list_id, title, now)
        return {"id": iid, "title": title}

    def toggle(self, item_id: str, now: datetime) -> dict:
        stamp = now.isoformat()
        with self.db.connect() as conn:
            r = conn.execute("SELECT * FROM list_items WHERE id = ?", (item_id,)).fetchone()
            if r is None:
                raise KeyError(item_id)
            done = 0 if r["done"] else 1
            if r["pending"] == "add":   # not in Reminders yet: just carry the check-off along with the add
                pending = "add"
            elif r["pending"] in ("done", "undone"):  # undoing a change Reminders hasn't seen: nothing to send
                pending = None
            else:
                pending = "done" if done else "undone"
            conn.execute("UPDATE list_items SET done = ?, done_at = ?, pending = ?, pending_at = ? WHERE id = ?",
                         (done, stamp if done else None, pending, stamp if pending else None, item_id))
        return {"id": item_id, "done": bool(done)}

    # ---------- the Mac helper ----------
    def changes(self, source: str = "apple") -> list[dict]:
        shown = {x for x in self.shown() if self.source_of(x) == source}
        out = []
        with self.db.connect() as conn:
            for r in conn.execute("SELECT * FROM list_items WHERE pending IS NOT NULL ORDER BY pending_at").fetchall():
                if r["list"] not in shown:
                    continue
                if r["pending"] == "add":
                    out.append({"op": "add", "local": r["id"], "list": r["list"], "title": r["title"], "notes": r["notes"],
                                "done": bool(r["done"])})
                else:
                    out.append({"op": "done", "local": r["id"], "ext": r["ext"], "done": r["pending"] == "done"})
        return out

    @staticmethod
    def _newer(a: Optional[str], b: Optional[str], now: datetime) -> bool:
        """Is time a (from Reminders) later than time b (a tap on the frame)?"""
        def parse(v):
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=now.tzinfo)
        try:
            return bool(a) and (not b or parse(a) > parse(b))
        except ValueError:
            return False

    def sync(self, body: dict, now: datetime, source: str = "apple") -> dict:
        """One check-in from a source: what's in Reminders (or Google Tasks) now, and which frame changes it has written there.

        body = {"lists": [{id, name, count}],                 every Reminders list (names only)
                "items": {list id: [{ext, title, notes, done, done_at, created, modified}]},   the shown lists
                "applied": [{"local": frame id, "ok": bool, "ext": Reminders id}]}
        Answers {"want": [list ids to send], "changes": [...]} for the Mac to write to Reminders.
        Lists from the other source are left alone.
        """
        prefix = ITEM_PREFIX[source]
        with self.db.connect() as conn:
            if isinstance(body.get("lists"), list):
                others = [a for a in self.available() if a["source"] != source]
                avail = [{"id": str(a["id"]), "name": str(a.get("name") or "List")[:80], "count": int(a.get("count") or 0),
                          "source": source} for a in body["lists"] if a.get("id")]
                self._set_meta(conn, "available", others + avail)
            self._set_meta(conn, self._synced_key(source), now.replace(tzinfo=None).isoformat(timespec="seconds"))

            for a in body.get("applied") or []:
                r = conn.execute("SELECT * FROM list_items WHERE id = ?", (a.get("local"),)).fetchone()
                if r is None:
                    continue
                if r["pending"] == "add":
                    ext = a.get("ext")
                    if a.get("ok") and ext:
                        if conn.execute("SELECT 1 FROM list_items WHERE id = ?", (prefix + ext,)).fetchone():
                            conn.execute("DELETE FROM list_items WHERE id = ?", (r["id"],))
                        else:
                            conn.execute("UPDATE list_items SET id = ?, ext = ?, pending = NULL, pending_at = NULL WHERE id = ?",
                                         (prefix + ext, ext, r["id"]))
                    elif not a.get("ok"):
                        conn.execute("DELETE FROM list_items WHERE id = ?", (r["id"],))
                else:
                    conn.execute("UPDATE list_items SET pending = NULL, pending_at = NULL WHERE id = ?", (r["id"],))

            for list_id, items in (body.get("items") or {}).items():
                seen = set()
                for it in items:
                    ext = str(it.get("ext") or "")
                    title = str(it.get("title") or "").strip()[:200]
                    if not ext or not title:
                        continue
                    rid = prefix + ext
                    seen.add(rid)
                    old = conn.execute("SELECT * FROM list_items WHERE id = ?", (rid,)).fetchone()
                    done, done_at = (1 if it.get("done") else 0), it.get("done_at")
                    pending, pending_at = None, None
                    if old is not None and old["pending"] in ("done", "undone") and not self._newer(it.get("modified"), old["pending_at"], now):
                        # The frame's check-off is newer and not in Reminders yet: keep it.
                        done, done_at, pending, pending_at = old["done"], old["done_at"], old["pending"], old["pending_at"]
                    if old is None:
                        self._remember(conn, list_id, title, now)
                    created = old["created"] if old is not None and old["created"] else it.get("created")
                    conn.execute(
                        "INSERT INTO list_items (id, list, ext, title, notes, done, done_at, created, modified, from_frame, pending, pending_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET list = excluded.list, title = excluded.title, "
                        "notes = excluded.notes, done = excluded.done, done_at = excluded.done_at, created = excluded.created, "
                        "modified = excluded.modified, from_frame = excluded.from_frame, pending = excluded.pending, pending_at = excluded.pending_at",
                        (rid, list_id, ext, title, str(it.get("notes") or "")[:300], done, done_at, created, it.get("modified"),
                         1 if FRAME_NOTE in str(it.get("notes") or "") else 0, pending, pending_at))
                # Gone from Reminders (deleted, or checked off more than two days ago): gone here too.
                for r in conn.execute("SELECT id FROM list_items WHERE list = ? AND id LIKE ?", (list_id, prefix + "%")).fetchall():
                    if r["id"] not in seen:
                        conn.execute("DELETE FROM list_items WHERE id = ? AND (pending IS NULL OR pending = 'add')", (r["id"],))
        return {"want": [x for x in self.shown() if self.source_of(x) == source], "changes": self.changes(source)}

    # ---------- demo mode ----------
    def seed_demo(self, now: datetime) -> None:
        if self.available():
            return
        lists = [{"id": "demo-groceries", "name": "Groceries", "count": 9}, {"id": "demo-todo", "name": "Family To-Do", "count": 4},
                 {"id": "demo-warehouse", "name": "Warehouse store", "count": 6}, {"id": "demo-work", "name": "Work (Dad)", "count": 23}]
        base = now.replace(tzinfo=None) - timedelta(hours=7)
        names = [("Bananas", ""), ("Strawberries", "2 pints"), ("Baby spinach", ""), ("Milk", "2 gallons, whole"), ("Eggs", "2 dozen"),
                 ("Shredded cheddar", FRAME_NOTE), ("Sandwich bread", ""), ("Peanut butter", "creamy"), ("Rice", "")]
        items = [{"ext": f"g{i}", "title": t, "notes": n, "done": False, "created": (base + timedelta(minutes=i)).isoformat()}
                 for i, (t, n) in enumerate(names)]
        items += [{"ext": "g90", "title": "Coffee filters", "done": True, "done_at": (now - timedelta(minutes=32)).isoformat()},
                  {"ext": "g91", "title": "Apples", "done": True, "done_at": (now - timedelta(hours=5, minutes=10)).isoformat()}]
        todo = [{"ext": f"t{i}", "title": t, "notes": "", "done": False} for i, t in
                enumerate(["Call the plumber", "Return library books", "Sign field trip form", "Pick up dry cleaning"])]
        self.sync({"lists": lists, "items": {"demo-groceries": items, "demo-todo": todo}}, now - timedelta(seconds=40))
        with self.db.connect() as conn:
            for t in ("Yogurt", "Yogurt bars", "Greek yogurt", "Bread", "Butter", "Cereal", "Paper towels"):
                self._remember(conn, "demo-groceries", t, now - timedelta(days=3))
