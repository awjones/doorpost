"""The screen time ledger: weekly math, good days, add/take away, undo, new week."""
from datetime import date, datetime

import pytest

from app import chores
from app import screentime as st

MON = date(2026, 10, 12)
THU_4PM = datetime(2026, 10, 15, 16, 12)


@pytest.fixture
def ledger(settings, db):
    st.ensure_started(db, datetime(2026, 10, 12, 8, 0))
    return settings, db


def test_week_math(ledger):
    settings, db = ledger
    cfg = settings.screen_time
    st.good_day(db, cfg, datetime(2026, 10, 12, 19, 0), "Mom")
    st.good_day(db, cfg, datetime(2026, 10, 13, 19, 0), "Dad")
    cid = [c for c in chores.scheduled(settings, MON) if c.kid == "child1"][0].id
    chores.claim(db, settings, cid, MON, datetime(2026, 10, 12, 17, 0))
    chore = chores.approve(db, settings, cid, MON, datetime(2026, 10, 12, 17, 5), "Dad")
    st.adjust(db, datetime(2026, 10, 14, 18, 0), "Mom", 10, "child2", "family", "Kind to a sibling")
    st.adjust(db, datetime(2026, 10, 14, 18, 5), "Dad", -15, "child3", "kid", "Not listening")
    st.adjust(db, datetime(2026, 10, 14, 18, 9), "Dad", -5, None, "family", "Fighting over the remote")

    s = st.summary(db, cfg, settings.kids, THU_4PM)
    assert s["pool"] == 60 + chore["minutes"] + 10 - 5
    assert s["total"] == s["pool"] + cfg.base_minutes
    assert s["kid_minutes"]["child1"] == chore["minutes"]
    assert s["kid_minutes"]["child2"] == 10
    assert s["kid_bonus"]["child3"] == -15          # just for Child 3: not in the family pool
    assert s["good_days"] == 2 and s["sleeps"] == 2 and not s["weekend"]
    labels = {p["short"]: p["minutes"] for p in s["parts"]}
    assert labels == {"to start": 180, "good days": 60, "chores": chore["minutes"], "extra": 5}
    assert s["saturday"] + s["sunday"] == s["total"]
    # a deduction that's just for one kid stays off the kitchen wall, but is in the parents' log
    assert all(not (e["scope"] == "kid" and e["minutes"] < 0) for e in s["feed"])
    assert any(e["title"] == "Not listening (just Child 3)" for e in s["log"])
    assert s["feed"][0]["title"] == "Fighting over the remote" and s["feed"][0]["by"] == "Dad"


def test_good_day_once_a_day_and_undo(ledger):
    settings, db = ledger
    cfg = settings.screen_time
    gd = st.good_day(db, cfg, datetime(2026, 10, 13, 19, 0), "Mom")
    with pytest.raises(st.ScreenTimeError, match="Mom already"):
        st.good_day(db, cfg, datetime(2026, 10, 13, 20, 0), "Dad")
    st.undo(db, gd["id"], datetime(2026, 10, 13, 20, 1), "Dad")
    with pytest.raises(st.ScreenTimeError, match="Already undone|Only"):
        st.undo(db, gd["id"], datetime(2026, 10, 13, 20, 2), "Dad")
    assert st.summary(db, cfg, settings.kids, THU_4PM)["pool"] == 0
    st.good_day(db, cfg, datetime(2026, 10, 13, 20, 5), "Dad")   # allowed again once undone
    s = st.summary(db, cfg, settings.kids, THU_4PM)
    assert s["pool"] == 30 and s["good_days"] == 1


def test_adjust_rules(ledger):
    settings, db = ledger
    now = datetime(2026, 10, 13, 9, 0)
    for minutes, kid, scope in [(0, None, "family"), (500, None, "family"), (5, None, "kid"), (5, None, "nope")]:
        with pytest.raises(st.ScreenTimeError):
            st.adjust(db, now, "Mom", minutes, kid, scope, "")
    st.adjust(db, now, "Mom", -30, None, "family", "")
    assert st.summary(db, settings.screen_time, settings.kids, THU_4PM)["pool"] == 0   # never below zero


def test_new_week_never_automatic_and_backdates_to_the_reminder(ledger):
    settings, db = ledger
    cfg = settings.screen_time
    st.good_day(db, cfg, datetime(2026, 10, 16, 19, 0), "Mom")
    sun_8pm = datetime(2026, 10, 18, 20, 0)
    assert not st.summary(db, cfg, settings.kids, sun_8pm)["new_week_due"]
    mon_8am = datetime(2026, 10, 19, 8, 0)
    s = st.summary(db, cfg, settings.kids, mon_8am)
    assert s["new_week_due"] and s["pool"] == 30      # still last week's: nobody pressed the button
    st.adjust(db, datetime(2026, 10, 19, 7, 30), "Dad", 5, "child1", "family", "Made breakfast")
    r = st.new_week(db, cfg, mon_8am, "Mom", last_total=210)
    assert r["started"] == "2026-10-18T21:00:00"      # from Sunday 9 PM, so Monday's 5 minutes count
    s = st.summary(db, cfg, settings.kids, mon_8am)
    assert s["pool"] == 5 and not s["new_week_due"]
    assert st.new_week(db, cfg, datetime(2026, 10, 19, 8, 3), "Dad")["already"]   # double tap
    weeks = st.history(db, settings.kids)
    assert weeks[0]["started_by"] == "Mom" and weeks[0]["pool"] == 5 and weeks[1]["pool"] == 30


def test_first_run_carries_in_this_weeks_approvals(settings, db):
    cid = [c for c in chores.scheduled(settings, MON) if c.kid == "child2"][0].id
    with db.connect() as conn:  # an approval from before the ledger existed
        conn.execute("INSERT INTO ledger (day, chore_id, kid, title, minutes, approved_at, approved_by) VALUES (?,?,?,?,?,?,?)",
                     (MON.isoformat(), cid, "child2", "Old one", 10, "2026-10-12T17:00:00-04:00", "Parent phone"))
        conn.execute("INSERT INTO ledger (day, chore_id, kid, title, minutes, approved_at, approved_by) VALUES (?,?,?,?,?,?,?)",
                     ("2026-10-05", cid, "child2", "Last week", 10, "2026-10-05T17:00:00-04:00", "Parent phone"))
    st.ensure_started(db, THU_4PM)
    st.ensure_started(db, THU_4PM)   # only once
    s = st.summary(db, settings.screen_time, settings.kids, THU_4PM)
    assert s["pool"] == 10 and s["kid_minutes"]["child2"] == 10


def test_settings_from_the_old_single_number():
    cfg = st.ScreenTimeSettings.from_store({"url": "http://old:8082", "weekend_base_minutes": 150})
    assert (cfg.base_saturday_minutes, cfg.base_sunday_minutes) == (75, 75)
    cfg = st.ScreenTimeSettings.from_store({"base_saturday_minutes": 60, "views": ["rocket", "bogus"]})
    assert cfg.base_saturday_minutes == 60 and cfg.views == ["rocket"]


def test_reminder_time():
    cfg = st.ScreenTimeSettings()
    assert st.reminder_at(cfg, datetime(2026, 10, 11, 21, 0)) == datetime(2026, 10, 18, 21, 0)
    assert st.reminder_at(cfg, datetime(2026, 10, 12, 0, 0)) == datetime(2026, 10, 18, 21, 0)


def test_summary_before_the_ledger_is_started(settings, db):
    assert st.summary(db, settings.screen_time, settings.kids, THU_4PM)["pool"] == 0
