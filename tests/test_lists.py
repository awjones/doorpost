"""Lists from Apple Reminders: the Mac helper's check-ins and changes made on the frame."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.db import Database
from app.lists import FRAME_NOTE, Lists, section_for

TZ = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 15, 16, 12, tzinfo=TZ)
AVAIL = [{"id": "G", "name": "Groceries", "count": 2}, {"id": "W", "name": "Work", "count": 9}]


def make(tmp_path, cfg=None):
    return Lists(Database(tmp_path / "t.db"), cfg)


def item(ext, title, done=False, modified="2026-10-15T20:00:00Z", **kw):
    return dict(ext=ext, title=title, done=done, modified=modified, created="2026-10-15T13:00:00Z", **kw)


def test_groceries_shown_by_default_and_snapshot(tmp_path):
    L = make(tmp_path)
    r = L.sync({"lists": AVAIL}, NOW)
    assert r == {"want": ["G"], "changes": []}           # first check-in: just the names
    L.sync({"lists": AVAIL, "items": {"G": [item("1", "Milk"), item("2", "Bananas"),
                                           item("3", "Coffee filters", True, done_at="2026-10-15T19:40:00Z")]}}, NOW)
    v = L.frame_view(NOW)
    g = v["lists"][0]
    assert v["home"] == "G" and g["name"] == "Groceries" and g["sections"] is True and g["open"] == 2
    assert [i["title"] for i in g["items"]] == ["Bananas", "Milk"]      # Produce before Dairy
    assert g["done"][0]["title"] == "Coffee filters" and g["done"][0]["when"] == "3:40 PM"
    assert v["synced"] == "just now" and v["stale"] is False
    # Removed in Reminders: removed here.
    L.sync({"items": {"G": [item("1", "Milk")]}}, NOW)
    assert [i["title"] for i in L.frame_view(NOW)["lists"][0]["items"]] == ["Milk"]


def test_frame_add_goes_to_the_mac_and_comes_back(tmp_path):
    L = make(tmp_path)
    L.sync({"lists": AVAIL, "items": {"G": []}}, NOW)
    new = L.add("G", "  Yogurt ", NOW)
    assert new["title"] == "Yogurt" and L.frame_view(NOW)["lists"][0]["items"][0]["waiting"] is True
    ch = L.sync({"items": {"G": []}}, NOW)["changes"]
    assert ch == [{"op": "add", "local": new["id"], "list": "G", "title": "Yogurt", "notes": FRAME_NOTE, "done": False}]
    # The Mac wrote it to Reminders and sends it back with its id.
    r = L.sync({"items": {"G": [item("9", "Yogurt", notes=FRAME_NOTE)]}, "applied": [{"local": new["id"], "ok": True, "ext": "9"}]}, NOW)
    assert r["changes"] == []
    items = L.frame_view(NOW)["lists"][0]["items"]
    assert [(i["id"], i["frame"], i["waiting"]) for i in items] == [("r:9", True, False)]
    assert "Yogurt" in L.frame_view(NOW)["lists"][0]["bought"]


def test_check_off_waits_for_reminders_and_newest_change_wins(tmp_path):
    L = make(tmp_path)
    L.sync({"lists": AVAIL, "items": {"G": [item("1", "Milk")]}}, NOW)
    L.toggle("r:1", NOW)
    # The Mac's next snapshot still says not done (older than the tap): the frame's check-off stays.
    r = L.sync({"items": {"G": [item("1", "Milk", modified="2026-10-15T19:00:00Z")]}}, NOW)
    assert r["changes"] == [{"op": "done", "local": "r:1", "ext": "1", "done": True}]
    assert L.frame_view(NOW)["lists"][0]["done"][0]["title"] == "Milk"
    # Applied: pending clears.
    L.sync({"items": {"G": [item("1", "Milk", True, done_at=NOW.isoformat())]}, "applied": [{"local": "r:1", "ok": True}]}, NOW)
    assert L.changes() == []
    # Tap again (un-check) and then someone edits it in Reminders later: Reminders wins.
    L.toggle("r:1", NOW)
    later = (NOW + timedelta(minutes=5)).isoformat()
    L.sync({"items": {"G": [item("1", "Milk", True, modified=later, done_at=NOW.isoformat())]}}, NOW)
    assert L.changes() == [] and L.frame_view(NOW)["lists"][0]["open"] == 0


def test_undo_before_sync_sends_nothing(tmp_path):
    L = make(tmp_path)
    L.sync({"lists": AVAIL, "items": {"G": [item("1", "Milk")]}}, NOW)
    L.toggle("r:1", NOW)
    L.toggle("r:1", NOW)
    assert L.changes() == []


def test_settings_pick_lists_and_home(tmp_path):
    L = make(tmp_path, {"shown": ["W", "G"], "home": "G", "sections": [], "anyone_add": False})
    L.sync({"lists": AVAIL, "items": {"W": [item("5", "Expense report")]}}, NOW)
    v = L.frame_view(NOW)
    assert [x["id"] for x in v["lists"]] == ["W", "G"] and v["home"] == "G" and v["can_add"] is False
    assert all(not x["sections"] for x in v["lists"])
    assert v["lists"][0]["items"][0]["title"] == "Expense report"


def test_sections():
    assert [section_for(t) for t in ("Baby spinach", "Peanut butter", "Ice cream", "Sandwich bread", "Watermelon", "Widgets")] == \
        ["Produce", "Pantry", "Frozen", "Bakery", "Produce", "Other"]
