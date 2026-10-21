"""Email updates: approving later in the week, undo, the schedule, the emails, quick approve links, Settings."""
import re
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import chores

WED, THU = date(2026, 10, 14), date(2026, 10, 15)
NOW = datetime(2026, 10, 15, 16, 0)
CHORE = "child2-set-the-table"


# ---------------- approving later in the week ----------------

def test_waiting_chore_from_yesterday_can_be_approved_today(settings, db):
    chores.claim(db, settings, CHORE, WED, datetime(2026, 10, 14, 17, 0))
    assert [c["id"] for c in chores.waiting_since(db, settings, chores.earliest_day(db, THU), WED)] == [CHORE]
    chores.approve_on(db, settings, CHORE, WED, NOW, "Dad")
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM screen_ledger WHERE chore_id=?", (CHORE,)).fetchone()
    assert (row["chore_day"], row["minutes"], row["at"][:10]) == ("2026-10-14", 5, "2026-10-15")   # counts this week


def test_an_earlier_day_only_takes_waiting_chores(settings, db):
    with pytest.raises(chores.ChoreError):   # never marked done: can't be approved after the day
        chores.approve_on(db, settings, CHORE, WED, NOW, "Dad")
    chores.approve_on(db, settings, CHORE, THU, NOW, "Dad")   # today works as before


def test_nothing_from_before_the_new_week(settings, db):
    chores.claim(db, settings, CHORE, WED, datetime(2026, 10, 14, 17, 0))
    with db.connect() as conn:   # a new week started Wednesday evening
        conn.execute("INSERT INTO screen_ledger (at, kind, minutes, note, by) VALUES ('2026-10-14T21:00:00', 'new_week', 0, 'New week', 'Mom')")
    assert chores.earliest_day(db, THU) == THU
    with pytest.raises(chores.ChoreError):
        chores.approve_on(db, settings, CHORE, WED, NOW, "Dad")


def test_undo_an_approval_and_approve_again(settings, db):
    from app import screentime as st
    chores.claim(db, settings, CHORE, THU, NOW)
    chores.approve(db, settings, CHORE, THU, NOW, "Dad (email)")
    pool = lambda: st.summary(db, settings.screen_time, settings.kids, NOW)["pool"]
    assert pool() == 5
    chores.unapprove(db, settings, CHORE, THU, NOW, "Dad (email)")
    assert pool() == 0
    assert {c["id"]: c["status"] for c in chores.chores_for(db, settings, THU)}[CHORE] == "waiting"
    chores.approve(db, settings, CHORE, THU, NOW, "Dad")
    assert pool() == 5   # credited again


# ---------------- the app ----------------

@pytest.fixture
def client(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T12:00:00")   # nothing due when the app starts
    import importlib
    import sys
    for m in ("app.admin", "app.admin_providers", "app.email_api"):
        sys.modules.pop(m, None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        yield c


def _setup(c, **daily):
    body = c.get("/api/admin/email-updates").json()
    body["daily"].update(daily)
    for p in body["people"]:
        p["email"] = f"{p['name'].lower()}@example.com"
    r = c.put("/api/admin/email-updates", json=body)
    assert r.status_code == 200, r.text
    return c.app.state.services


def _at(s, hh, mm, day=THU):
    from zoneinfo import ZoneInfo
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=ZoneInfo(s.settings.timezone))


def test_parents_are_listed_and_need_an_address(client):
    v = client.get("/api/admin/email-updates").json()
    assert [(p["name"], p["parent"], p["email"]) for p in v["people"]] == [("Dad", True, ""), ("Mom", True, "")]
    assert v["daily"]["time"] == "19:30" and v["weekly"]["day"] == "fri" and v["daily"]["quick_approve"] is True
    bad = dict(v, people=[dict(v["people"][0], email="not an address")])
    assert client.put("/api/admin/email-updates", json=bad).status_code == 400


def test_daily_recap_goes_once_with_a_line_per_waiting_chore(client):
    from app import email_updates as eu
    s = _setup(client)
    chores.claim(s.db, s.settings, CHORE, THU, _at(s, 17, 5))
    assert "daily" not in [k for k, _p in eu.due(s, _at(s, 19, 29))]   # not before its time
    sent = eu.tick(s, _at(s, 19, 31))
    assert ("daily", "2026-10-15", "sent") in sent
    to = sorted(m["to"] for m in s.mailer.outbox)
    assert to == ["dad@example.com", "mom@example.com"]
    msg = s.mailer.outbox[0]
    assert "waiting for you" in msg["subject"] and "Set the table" in msg["html"] and "Approve all" in msg["html"]
    assert eu.tick(s, _at(s, 19, 40)) == []                 # never twice
    assert len(s.mailer.outbox) == 2
    assert eu.tick(s, _at(s, 22, 0)) == []                  # and not after the window


def test_morning_recap_covers_yesterday(client):
    from app import email_updates as eu
    s = _setup(client, time="07:00")
    assert ("daily", "2026-10-14") in eu.due(s, _at(s, 7, 5))


def test_a_day_with_nothing_is_skipped(client):
    from app import email_updates as eu
    s = _setup(client)
    with s.db.connect() as conn:
        conn.execute("DELETE FROM chore_status")
    assert eu.tick(s, _at(s, 19, 31)) == [("daily", "2026-10-15", "skipped")]
    assert s.mailer.outbox == []


def _link(msg, which):
    m = re.search(r'/e/([A-Za-z0-9_-]{20,})\?' + which, msg["html"])
    assert m, "no quick approve link"
    return m.group(1)


def test_quick_approve_link(client):
    from app import email_updates as eu
    s = _setup(client)
    chores.claim(s.db, s.settings, CHORE, THU, _at(s, 17, 5))
    eu.tick(s, _at(s, 19, 31))
    dad = next(m for m in s.mailer.outbox if m["to"] == "dad@example.com")
    token = _link(dad, "all=1")
    v = client.get(f"/api/email/link/{token}").json()
    idx = next(i["idx"] for i in v["items"] if i["title"] == "Set the table")
    assert v["state"] == "ready" and v["parent"] == "Dad"
    # Opening the page (what a mail scanner does) approves nothing.
    page = client.get(f"/e/{token}?c={idx}")
    assert page.status_code == 200 and "api/email/link/" in page.text
    assert next(i for i in client.get(f"/api/email/link/{token}").json()["items"] if i["idx"] == idx)["status"] == "waiting"
    # No PIN or session needed: a fresh client with no cookie.
    with TestClient(client.app) as stranger:
        r = stranger.post(f"/api/email/link/{token}/approve", json={"items": [idx]})
        assert r.status_code == 200, r.text
        assert [a["title"] for a in r.json()["approved"]] == ["Set the table"]
        again = stranger.post(f"/api/email/link/{token}/approve", json={"items": [idx]}).json()
        assert again["approved"] == []                          # once each
        with s.db.connect() as conn:
            assert conn.execute("SELECT approved_by FROM chore_status WHERE chore_id=?", (CHORE,)).fetchone()[0] == "Dad (email)"
        r = stranger.post(f"/api/email/link/{token}/undo", json={"idx": idx})
        assert r.status_code == 200
        assert next(i for i in r.json()["items"] if i["idx"] == idx)["status"] == "waiting"
        assert stranger.post("/api/email/link/not-a-real-token/approve", json={"all": True}).status_code == 404


def test_links_expire_after_48_hours(client):
    from app import email_updates as eu
    s = _setup(client)
    chores.claim(s.db, s.settings, CHORE, THU, _at(s, 17, 5))
    eu.tick(s, _at(s, 19, 31))
    token = _link(s.mailer.outbox[0], "all=1")
    later = _at(s, 19, 31) + timedelta(hours=49)
    assert eu.link_view(s, token, later)["state"] == "expired"
    with pytest.raises(eu.LinkError):
        eu.link_approve(s, token, [0], later)


def test_quick_approve_can_be_turned_off(client):
    from app import email_updates as eu
    s = _setup(client, quick_approve=False)
    chores.claim(s.db, s.settings, CHORE, THU, _at(s, 17, 5))
    eu.tick(s, _at(s, 19, 31))
    assert "/e/" not in s.mailer.outbox[0]["html"] and "/parent" in s.mailer.outbox[0]["html"]


def test_someone_who_is_not_a_parent_never_gets_buttons(client):
    from app import email_updates as eu
    body = client.get("/api/admin/email-updates").json()
    body["people"] = [{"name": "Grandma", "email": "grandma@example.com", "other": True, "daily": True, "weekly": True, "reminder": False}]
    assert client.put("/api/admin/email-updates", json=body).status_code == 200
    s = client.app.state.services
    chores.claim(s.db, s.settings, CHORE, THU, _at(s, 17, 5))
    eu.tick(s, _at(s, 19, 31))
    assert [m["to"] for m in s.mailer.outbox] == ["grandma@example.com"]
    assert "/e/" not in s.mailer.outbox[0]["html"]


def test_weekend_email_has_a_line_per_kid(client):
    from app import email_updates as eu
    from app import screentime as st
    s = _setup(client)
    st.adjust(s.db, _at(s, 12, 0), "Mom", 20, "child2", "kid", "Extra help")
    fri = date(2026, 10, 16)
    assert ("weekly", "2026-10-16") in eu.due(s, _at(s, 16, 5, fri))
    d = s.screen()
    lines = {l["kid"].id: l for l in eu.kid_lines(d, {k.id: k for k in s.settings.kids})}
    assert lines["child2"]["saturday"] == d["saturday"] + 20 and lines["child1"]["saturday"] == d["saturday"]
    msg = eu.compose_weekly(s, eu.week_data(s, _at(s, 16, 5, fri)), _at(s, 16, 5, fri))
    assert "Set this on each device" in msg["html"] and "just for Child 2" in msg["html"]
    assert msg["subject"].startswith("Weekend screen time: Sat ")


def test_new_week_reminder_only_when_due(client):
    from app import email_updates as eu
    s = _setup(client)
    start, _m, _r = __import__("app.screentime", fromlist=["x"]).week_rows(s.db)
    due_at = __import__("app.screentime", fromlist=["x"]).reminder_at(s.settings.screen_time, datetime.fromisoformat(start))
    from zoneinfo import ZoneInfo
    at = due_at.replace(tzinfo=ZoneInfo(s.settings.timezone)) + timedelta(minutes=1)
    assert ("reminder", start) in eu.due(s, at)
    assert ("reminder", start) not in eu.due(s, at - timedelta(hours=1))


def test_account_password_is_never_sent_back(client):
    r = client.put("/api/admin/email-updates/account", json={"provider": "gmail", "user": "dad@example.com", "password": "abcd efgh ijkl mnop"})
    assert r.status_code == 200, r.text
    v = client.get("/api/admin/email-updates")
    assert v.json()["account"]["password_set"] is True and v.json()["account"]["ready"] is True
    assert "abcd" not in v.text and "mnop" not in v.text
    s = client.app.state.services
    assert s.settings.smtp_password == "abcdefghijklmnop"    # Google shows app passwords with spaces


def test_send_a_test_and_preview(client):
    _setup(client)
    r = client.post("/api/admin/email-updates/test", json={"kind": "weekly", "name": "Mom"})
    assert r.status_code == 200 and r.json()["subject"].startswith("TEST · ")
    assert client.get("/api/admin/email-updates/preview/daily").status_code == 200
    log = client.get("/api/admin/email-updates").json()["log"]
    assert log[0]["kind"] == "test" and log[0]["recipients"] == "Mom"


def test_parent_page_lists_chores_still_waiting_from_earlier(client):
    s = client.app.state.services
    chores.claim(s.db, s.settings, CHORE, WED, datetime(2026, 10, 14, 17, 0))
    d = client.get("/api/parent/summary").json()
    assert [(c["id"], c["day"], c["day_label"]) for c in d["earlier"]] == [(CHORE, "2026-10-14", "Wed")]
    assert client.post(f"/api/parent/chores/{CHORE}/approve?day=2026-10-14").status_code == 200
    assert client.get("/api/parent/summary").json()["earlier"] == []


def test_settings_page_is_in_the_menu(client):
    assert client.get("/admin/email-updates").status_code == 200
    assert "email-admin.js" in client.get("/admin/email-updates").text
