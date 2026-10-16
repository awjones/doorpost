from datetime import date, datetime

import pytest

from app import chores

THU = date(2026, 10, 15)
SAT = date(2026, 10, 17)
NOW = datetime(2026, 10, 15, 16, 0)


def test_schedule_respects_days(settings):
    thu = {c.id for c in chores.scheduled(settings, THU)}
    sat = {c.id for c in chores.scheduled(settings, SAT)}
    assert "child1-practice-piano" in thu          # mon-thu
    assert "child1-make-your-bed" not in sat       # weekdays only
    assert "child3-put-your-shoes-away" in sat  # daily


def test_claim_then_approve_writes_ledger(settings, db):
    cid = "child2-set-the-table"
    assert chores.claim(db, settings, cid, THU, NOW) == "waiting"
    assert chores.claim(db, settings, cid, THU, NOW) == "waiting"  # idempotent
    status = {c["id"]: c["status"] for c in chores.chores_for(db, settings, THU, "child2")}
    assert status[cid] == "waiting"

    chores.approve(db, settings, cid, THU, NOW, "Parent PIN on frame")
    status = {c["id"]: c["status"] for c in chores.chores_for(db, settings, THU, "child2")}
    assert status[cid] == "done"
    assert chores.local_week_minutes(db, "child2", THU)["thu"] == 5
    with db.connect() as conn:   # credited to screen time in the same step
        row = conn.execute("SELECT * FROM screen_ledger WHERE chore_id = ?", (cid,)).fetchone()
    assert (row["kind"], row["kid"], row["minutes"], row["scope"]) == ("chore", "child2", 5, "family")


def test_cannot_approve_twice(settings, db):
    chores.approve(db, settings, "child2-set-the-table", THU, NOW, "x")
    with pytest.raises(chores.ChoreError):
        chores.approve(db, settings, "child2-set-the-table", THU, NOW, "x")


def test_send_back_returns_to_todo(settings, db):
    chores.claim(db, settings, "child1-tidy-your-room", THU, NOW)
    chores.send_back(db, "child1-tidy-your-room", THU)
    status = {c["id"]: c["status"] for c in chores.chores_for(db, settings, THU, "child1")}
    assert status["child1-tidy-your-room"] == "todo"


def test_unknown_or_unscheduled_chore_rejected(settings, db):
    with pytest.raises(chores.ChoreError):
        chores.claim(db, settings, "nope", THU, NOW)
    with pytest.raises(chores.ChoreError):
        chores.claim(db, settings, "child1-make-your-bed", SAT, NOW)


def test_week_is_monday_to_sunday():
    assert chores.week_bounds(THU) == (date(2026, 10, 12), date(2026, 10, 18))
