"""Bible translations for the Faith pack's verses (app/bible.py, docs/bible-translations.md)."""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import bible as B
from app import pack_build as pb

SAMPLE = B.BSB_SAMPLE.read_text(encoding="utf-8")


# ---------------- references, words and shortening ----------------

def test_references():
    assert B.parse_ref("Lamentations 3:22–23") == ["Lamentations 3:22", "Lamentations 3:23"]
    assert B.parse_ref("Psalms 150:6") == ["Psalm 150:6"]
    assert B.parse_ref("Jude 3") == ["Jude 1:3"] and B.parse_ref("Obadiah 1:21") == ["Obadiah 1:21"]
    assert B.parse_ref("Song of Solomon 2:1") == ["Song of Solomon 2:1"]
    assert B.parse_ref("Psalm 23") == [] and B.parse_ref("Hezekiah 1:1") == [] and B.parse_ref("") == []
    assert B.canon("Numbers 6:24–25") == "Numbers 6:24-25" and B.canon("Psalms 23:1") == "Psalm 23:1"


def test_every_quote_has_a_passage_and_resolves_in_kjv():
    quotes = pb.faith_quotes()
    assert len(quotes) == 182   # 183 in the review, less Good Friday's bare reference
    kjv = B.Bible("kjv", {"kjv": json.loads(B.KJV_FILE.read_text())["verses"]})
    for text, ref in quotes:
        p = pb.passage(text, ref)
        assert p and p["verses"] and p["tr"] == "esv", ref
        assert set(p["short"]) == {"kjv", "bsb"}, ref                     # stored word ranges, not a guess
        out, cite, code = kjv.show(p)
        assert code == "kjv" and cite.endswith("(KJV)") and out[-1] in ".?!’", (ref, out)
        assert len(out) <= 2.6 * len(text) + 20, (ref, out)              # shortened like the pack's quote


def test_kjv_text_is_the_public_domain_text():
    data = json.loads(B.KJV_FILE.read_text())
    assert "public domain" in data["source"].lower() and "openbible.com" in data["source"]
    v = data["verses"]
    assert set(v) == set(B.verse_list()) and len(v) == 173
    assert v["Exodus 20:13"] == "Thou shalt not kill."
    assert v["1 Peter 5:7"] == "Casting all your care upon him; for he careth for you."
    assert not any("[" in t or "]" in t for t in v.values())          # the printed italics' brackets are gone


def test_shortening_keeps_the_same_cut():
    full = "Every good gift and every perfect gift is from above, and cometh down from the Father of lights, with whom is no variableness"
    keep = B.align("Every good gift... coming down from the Father of lights", full)
    assert len(keep) == 2 and B.excerpt(full, keep).startswith("Every good gift... ")
    assert B.tidy("“I am the bread of life.") == "I am the bread of life."
    assert B.tidy("let your ‘Yes’ be ‘Yes,’ and your ‘No,’ ‘No.’") == "Let your ‘Yes’ be ‘Yes,’ and your ‘No,’ ‘No.’"
    assert B.tidy("the righteous will live by faith—") == "The righteous will live by faith."


def test_bsb_names_only_whole_verses():
    src = {"bsb": B.parse_plain(SAMPLE)}
    b = B.Bible("bsb", src)
    whole = pb.passage("In peace I will both lie down and sleep; for you alone, O Lord, make me dwell in safety.", "Psalm 4:8")
    short = pb.passage("No greater joy than to hear that my children are walking in the truth", "3 John 1:4")
    assert b.show(whole)[1] == "Psalm 4:8 (BSB)"
    text, cite, code = b.show(short)
    assert code == "bsb" and cite == "3 John 1:4 (adapted)" and "BSB" not in cite
    assert text == "No greater joy than to hear that my children are walking in the truth."


def test_fallback_order():
    p = pb.passage("The Lord is my shepherd; I shall not want", "Psalm 23:1")
    kjv = json.loads(B.KJV_FILE.read_text())["verses"]
    # BSB chosen but not downloaded: KJV
    assert B.Bible("bsb", {"kjv": kjv}).show(p)[2] == "kjv"
    # BSB downloaded but this verse isn't in it: KJV
    assert B.Bible("bsb", {"kjv": kjv, "bsb": B.parse_plain(SAMPLE)}).show(p)[2] == "kjv"
    # nothing on hand at all: the pack's own (ESV) text
    assert B.Bible("nasb", {}).show(p) == ("The Lord is my shepherd; I shall not want.", "Psalm 23:1 (ESV)", "esv")
    # a pack verse with no passage (an older pack) shows its line as it was
    assert B.Bible("kjv", {"kjv": kjv}).line(None, "“Old.” Psalm 1:1") == "“Old.” Psalm 1:1"
    # your own text, as given; a whole verse much longer than the quote is cut down to match
    own = B.Bible("nasb", {"kjv": kjv}, {"nasb": {"Psalm 23:1": "Mine, as given"}})
    assert own.show(p)[:2] == ("Mine, as given.", "Psalm 23:1 (NASB)")
    long = B.Bible("nasb", {}, {"nasb": {"Psalm 23:1": "A Psalm of David. The LORD is my shepherd, I will not be in need. "
                                                       "He lets me lie down in green pastures; He leads me beside quiet waters."}})
    assert long.show(p)[0] == "The LORD is my shepherd, I will not be in need."


# ---------------- getting the BSB ----------------

class FakeStream:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_bytes(self):
        for i in range(0, len(self.body), 500):
            yield self.body[i:i + 500]


def test_bsb_download_parses_the_official_file(demo_env, monkeypatch):
    import httpx
    seen = {}

    def fake_stream(method, url, **kw):
        seen["url"] = url
        return FakeStream(("﻿" + SAMPLE + "Genesis 50:26\tSo Joseph died at the age of 110.\n").encode("utf-8"))
    monkeypatch.setattr(httpx, "stream", fake_stream)
    n = B.download_bsb(demo=False)
    assert seen["url"] == "https://bereanbible.com/bsb.txt"
    data = json.loads((B.bible_dir(False) / "bsb.json").read_text())
    assert n == len(data["verses"]) == 33 and "Genesis 50:26" not in data["verses"]   # only the verses the pictures use
    assert data["verses"]["Psalm 4:8"].startswith("I will lie down and sleep in peace")
    st = {t["code"]: t for t in B.status(False)}
    assert st["bsb"]["state"] == "downloaded" and "33 verses" in st["bsb"]["label"]
    B.remove(False, "bsb")
    assert {t["code"]: t for t in B.status(False)}["bsb"]["state"] == "download"


def test_bsb_download_refuses_the_wrong_file(demo_env, monkeypatch):
    import httpx
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: FakeStream(b"<html>not the file</html>"))
    with pytest.raises(ValueError, match="didn't have any"):
        B.download_bsb(demo=False)


# ---------------- Settings and the frame ----------------

@pytest.fixture
def admin(demo_env, monkeypatch):
    monkeypatch.setenv("FRAME_NOW", "2026-10-18T10:00:00")
    import importlib
    import sys
    for m in ("app.admin", "app.admin_providers", "app.bible_api"):
        sys.modules.pop(m, None)
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        assert c.post("/api/parent/unlock?remember=1", json={"pin": "1234"}).status_code == 200
        yield c


def _sunday(c):
    return next(x for x in c.get("/api/calendar?view=rolling&offset=0").json()["days"] if x["date"] == "2026-10-18")["special"]


def test_switching_translation_changes_the_popup_and_the_clock(admin):
    sp = _sunday(admin)
    assert sp["verse"] == "“No greater joy than to hear that my children are walking in the truth.” 3 John 1:4 (ESV)"
    clock = admin.get("/api/frame").json()["clock_verses"]
    assert clock[0] == ["In peace I will both lie down and sleep; for you alone, O Lord, make me dwell in safety.", "Psalm 4:8 (ESV)"]

    assert admin.put("/api/admin/bible", json={"translation": "kjv"}).status_code == 200
    assert _sunday(admin)["verse"] == "“No greater joy than to hear that my children walk in truth.” 3 John 1:4 (KJV)"
    assert admin.get("/api/frame").json()["clock_verses"][0] == [
        "I will both lay me down in peace, and sleep: for thou, LORD, only makest me dwell in safety.", "Psalm 4:8 (KJV)"]

    # BSB before it's downloaded: KJV; after (demo mode reads the sample, no network): BSB
    assert admin.put("/api/admin/bible", json={"translation": "bsb"}).status_code == 200
    assert _sunday(admin)["verse"].endswith("(KJV)")
    r = admin.post("/api/admin/bible/bsb/download")
    assert r.status_code == 200 and r.json()["verses"] == 33
    assert _sunday(admin)["verse"] == "“No greater joy than to hear that my children are walking in the truth.” 3 John 1:4 (adapted)"
    assert admin.get("/api/frame").json()["clock_verses"][0][1] == "Psalm 4:8 (BSB)"

    # church-year days and Thanksgiving follow too
    import app.main
    s = app.main.app.state.services.special
    assert s.for_day(date(2026, 10, 31), [], date(2026, 10, 18))[0]["verse"] == "“The righteous will live by faith.” Romans 1:17 (adapted)"
    assert s.for_day(date(2026, 11, 26), [], date(2026, 10, 18))[0]["verse"] == "“Give thanks to the LORD, for He is good.” Psalm 107:1 (adapted)"

    # removing the BSB falls back to the KJV
    assert admin.delete("/api/admin/bible/bsb").status_code == 200
    assert _sunday(admin)["verse"].endswith("(KJV)")
    assert admin.put("/api/admin/bible", json={"translation": "xyz"}).status_code == 400


def test_settings_show_status_and_notices(admin):
    v = admin.get("/api/admin/bible").json()
    assert v["choice"] == "esv" and v["has_verses"] and v["verses"] > 150
    t = {x["code"]: x for x in v["translations"]}
    assert t["esv"]["notice"].startswith("Scripture quotations are from the ESV® Bible (The Holy Bible, English Standard Version®), © 2001 by Crossway")
    assert "ESV Text Edition: 2025" in t["esv"]["notice"] and "Used by permission. All rights reserved." in t["esv"]["notice"]
    assert "Creative Commons" in t["esv"]["note"] and "permission" in t["esv"]["note"]
    assert ["Crossway permission request", "https://www.crossway.org/permissions/digital/"] in t["esv"]["links"]
    assert ["esv.org", "https://www.esv.org"] in t["esv"]["links"]
    assert t["bsb"]["notice"] == "Bible quotations from the Berean Standard Bible (BSB), public domain."
    assert "adapted" in t["bsb"]["note"] and t["bsb"]["state"] == "download"
    assert t["kjv"]["state"] == "built-in" and "public domain" in t["kjv"]["notice"]
    assert t["nasb"]["state"] == "needs-text" and "The Lockman Foundation" in t["nasb"]["notice"] and "2020" in t["nasb"]["notice"]
    assert admin.put("/api/admin/bible", json={"nasb_edition": "1995"}).status_code == 200
    t = {x["code"]: x for x in admin.get("/api/admin/bible").json()["translations"]}
    assert "1995 by The Lockman" in t["nasb"]["notice"]
    assert [p["code"] for p in v["preview"]] == ["esv", "kjv", "bsb", "nasb"] and v["preview"][1]["cite"] == "Psalm 118:24 (KJV)"
    page = admin.get("/admin/special-days").text
    assert "bible-admin.js" in page and "bible-admin.css" in page


def test_nasb_your_own_text_and_key(admin, monkeypatch):
    tpl = admin.get("/api/admin/bible/template.json").json()
    assert tpl["Psalm 118:24"] and len(tpl) > 150
    own = json.dumps({"3 John 1:4": "Your licensed text for this verse", "Not a ref": "x"}).encode()
    r = admin.post("/api/admin/bible/nasb/import", files={"file": ("nasb.json", own, "application/json")})
    assert r.status_code == 200 and r.json()["verses"] == 1
    assert admin.put("/api/admin/bible", json={"translation": "nasb"}).status_code == 200
    assert _sunday(admin)["verse"] == "“Your licensed text for this verse.” 3 John 1:4 (NASB)"
    assert admin.get("/api/frame").json()["clock_verses"][0][1] == "Psalm 4:8 (KJV)"   # not in your text: KJV
    bad = admin.post("/api/admin/bible/nasb/import", files={"file": ("x.json", b"[1,2]", "application/json")})
    assert bad.status_code == 400
    # the key is saved with the secrets and never sent back
    assert admin.put("/api/admin/bible/apibible", json={"key": "secret-key-123", "bible_id": "abcdef123456-01"}).status_code == 200
    v = admin.get("/api/admin/bible").json()
    assert v["apibible"] == {"key_set": True, "bible_id": "abcdef123456-01"} and "secret-key-123" not in json.dumps(v)
    assert admin.post("/api/admin/bible/nasb/fetch").status_code == 400   # off in demo mode
    assert admin.put("/api/admin/bible/apibible", json={"bible_id": "no spaces allowed"}).status_code == 400


def test_apibible_fetch(demo_env, monkeypatch):
    import httpx
    calls = []

    class Resp:
        def __init__(self, url):
            self.url = url
            self.status_code = 200 if "PSA.4.8" in url else 404

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"content": "  [8] In peace I will lie down and sleep. "}}

    class Client:
        def __init__(self, **kw):
            calls.append(kw["headers"])

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            assert params["content-type"] == "text"
            return Resp(url)
    monkeypatch.setattr(httpx, "Client", Client)
    assert B.fetch_apibible(False, "k-123", "abcdef123456-01") == 1
    assert calls == [{"api-key": "k-123"}]
    data = json.loads((B.bible_dir(False) / "nasb.json").read_text())
    assert data["verses"] == {"Psalm 4:8": "In peace I will lie down and sleep."} and not data.get("as_is")
    with pytest.raises(ValueError):
        B.fetch_apibible(True, "k", "abcdef123456-01")


def test_faith_pack_keeps_reference_and_shortening(tmp_path):
    folder = pb.build("faith", tmp_path)
    m = json.loads((folder / "pack.json").read_text())
    assert m["license"] == "CC BY 4.0" and m["version"] == "1.1.1"
    clock = next(r for r in m["rules"] if r.get("clock_verses"))
    assert len(clock["passages"]) == len(clock["clock_verses"]) == 7
    palm = next(r for r in m["rules"] if r.get("church") == "palm")
    assert palm["passage"]["ref"] == "Mark 11:9" and palm["passage"]["tr"] == "esv" and palm["verse"].startswith("“Blessed")
    gf = next(r for r in m["rules"] if r.get("church") == "goodfriday")
    assert "passage" not in gf and gf["verse"] == "John 19:30"
    series = json.loads((folder / "series.json").read_text())
    it = series["series"][0]["items"][0]
    assert it["passage"]["verses"] == ["Psalm 118:24"] and it["passage"]["short"]["kjv"]["keep"] == [[0, 9]]
    assert it["verse"] == "This is the day that the Lord has made"   # the ESV text the pack ships today, unchanged
