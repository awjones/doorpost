"""Birthday portraits, the new special-day pictures, and first-day-of-season days."""
import io
from datetime import date

from PIL import Image

from app import portraits as pt
from app import special as sp
from app.scenes_family import NAMES, THEMES, WORDS

PEOPLE = [{"slug": "child1", "name": "Child 1", "aliases": [], "kid": "child1"},
          {"slug": "child-3", "name": "Child 3", "aliases": ["Buddy"], "kid": "child3"},
          {"slug": "mom", "name": "Mom", "aliases": [], "kid": None}]


def jpeg(color=(200, 120, 60), size=(1200, 900)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


def test_birthday_titles_find_the_person():
    assert pt.match_person("Child 1's 10th Birthday", PEOPLE)["slug"] == "child1"
    assert pt.match_person("🎂 Buddy turns 6", PEOPLE)["slug"] == "child-3"
    assert pt.match_person("Birthday – Child 3", PEOPLE)["slug"] == "child-3"
    assert pt.match_person("Grandchild 1's birthday", PEOPLE) is None   # "child 1" inside "Grandchild 1" isn't Child 1
    assert pt.birthday_name("Mom’s Birthday!", PEOPLE) == "Mom"
    assert pt.birthday_name("Grandma's 80th birthday party", PEOPLE) == "Grandma"


def test_crop_puts_the_face_in_the_upper_middle():
    l, t, r, b = pt.portrait_crop((1600, 1200), (0.7, 0.4, 0.2))
    assert abs((r - l) / (b - t) - 1.0) < 0.01                             # square (shown as a circle)
    assert l <= 0.7 * 1600 <= r and t <= 0.4 * 1200 <= b
    face_share = 0.2 * 1200 / (b - t)
    assert 0.35 < face_share < 0.5
    l, t, r, b = pt.portrait_crop((1600, 1200), None)                      # no face: full height, centered
    assert b - t == 1200 and abs((l + r) / 2 - 800) <= 1


def test_store_keeps_hand_picked_over_the_macs(tmp_path):
    store = pt.Portraits(tmp_path)
    im = Image.open(io.BytesIO(jpeg()))
    store.save("Child 1", im, "upload")
    assert store.save("child-1", im, "apple", auto=True) == {"ok": True, "kept": "upload"}
    assert store.index()["child-1"]["source"] == "upload"
    assert store.url("child-1").startswith("portraits/child-1.jpg?v=1")
    with Image.open(store.path("child-1")) as out:
        assert out.size == (pt.OUT_W, pt.OUT_H)
    store.save("mom", im, "apple", taken="2026-05-01T10:00:00", ref="ABC", auto=True)
    store.save("mom", im, "apple", taken="2026-07-01T10:00:00", ref="DEF", auto=True)
    assert store.index()["mom"]["ref"] == "DEF" and store.index()["mom"]["v"] == 2
    assert store.remove("mom") and store.path("mom") is None


def test_best_portrait_falls_back_to_the_newest():
    a, b = Image.new("RGB", (400, 400), "red"), Image.new("RGB", (400, 400), "blue")
    im, taken, face = pt.best_portrait([(a, "2025-01-01T00:00:00Z"), (b, "2026-02-01T00:00:00Z")])
    assert im is b and taken.startswith("2026") and face is None
    assert pt.best_portrait([]) is None


def test_new_pictures_have_names_words_and_placeholders():
    assert set(THEMES) <= sp.THEMES and set(NAMES) == set(THEMES)
    svg = THEMES["birthday"]()
    assert "{{NAME}}" in svg and "{{PORTRAIT}}" in svg and "{{NAME_SIZE}}" in svg
    assert all(k in THEMES for _, k in WORDS)
    words = sp.DEFAULT_WORDS
    assert sp.flag_event("Child 1's Birthday", "", words)[1] == "birthday"
    assert sp.flag_event("Church picnic", "", words)[1] == "picnic"
    assert sp.flag_event("Pinewood Derby", "", words)[1] == "pinewood"
    assert sp.flag_event("Beach day", "", words)[1] == "beach"            # the old words still work
    assert sp.flag_event("Soccer practice", "", words)[1] is None          # everyday: not special by itself...
    assert sp.flag_event("⭐ Soccer tournament", "", words)[1] == "soccer"   # ...but starred, it gets the picture
    assert sp.flag_event("Vacation at Grandma's", "", words)[1] == "trip"


def test_photo_none_keeps_an_event_ordinary():
    words = sp.DEFAULT_WORDS
    assert sp.flag_event("Water park", "photo: none", words) == ("Water park", None, "")
    assert sp.flag_event("⭐ Water park", "Bring sunscreen\nphoto: off", words) == ("Water park", None, "Bring sunscreen")
    assert sp.flag_event("Child 1's birthday", "photo: none", words, PEOPLE)[1] is None
    assert sp.flag_event("Water park", "", words)[1] == "waterpark"


def test_only_our_birthdays_take_over_the_day():
    words = sp.DEFAULT_WORDS
    for title in ("Child 1's 10th Birthday", "Child 1 Example’s Birthday", "Birthday: Buddy", "Happy birthday, Child 3", "Buddy turns 6"):
        assert sp.flag_event(title, "", words, PEOPLE)[1] == "birthday", title
    for title in ("Birthday party (Buddy)", "Mia's birthday party", "Grandchild 1's birthday"):
        assert sp.flag_event(title, "", words, PEOPLE)[1] is None, title
    assert sp.flag_event("⭐ Mia's birthday party", "", words, PEOPLE)[1] == "birthday"


def test_season_days_2026():
    days = sp.season_days(2026, "America/New_York")
    assert days[date(2026, 3, 20)][0] == "spring"
    assert days[date(2026, 6, 21)][0] == "summer"
    assert days[date(2026, 9, 22)][0] == "fall"
    assert days[date(2026, 12, 21)][0] == "winter"


class _NoHolidays:
    days, url, error = [], "", None


def _days(**cfg):
    return sp.SpecialDays(dict(cfg), _NoHolidays(), sp.Path("/nonexistent"), people=PEOPLE,
                          portrait=lambda p: f"portraits/{p['slug']}.jpg?v=3")


def test_birthday_special_has_name_and_portrait():
    ev = {"title": "Child 1's 10th Birthday", "look": "birthday", "all_day": True, "time": "All day", "uid": "x"}
    special, _ = _days().for_day(date(2026, 10, 20), [ev], date(2026, 10, 15))
    assert special["theme"] == "birthday" and special["name"] == "Child 1"
    assert special["portrait"] == "portraits/child1.jpg?v=3" and special["script"] == "Happy birthday, Child 1!"
    ev["title"] = "Grandma's birthday"
    special, _ = _days().for_day(date(2026, 10, 20), [ev], date(2026, 10, 15))
    assert special["name"] == "Grandma" and special["portrait"] is None


def test_first_day_of_fall_is_special_unless_turned_off():
    special, _ = _days().for_day(date(2026, 9, 22), [], date(2026, 9, 20))
    assert special["kind"] == "season" and special["theme"] == "fall" and special["countdown"] == ""
    assert _days(seasons=False).for_day(date(2026, 9, 22), [], date(2026, 9, 20))[0] is None



def test_heic_uploads_open():
    pillow_heif = __import__("pillow_heif")
    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "green").save(buf, "HEIF")
    assert pt.open_image(buf.getvalue()).size == (300, 200)


def test_every_picture_is_in_a_group_with_a_write_up():
    from app import picture_guide as pg
    grouped = [k for _, keys in pg.GROUPS for k in keys]
    assert set(grouped) | {"vacation"} == sp.THEMES and len(grouped) == len(set(grouped))
    for g in pg.guide(sp.THEMES, sp.DEFAULT_WORDS):
        for it in g["items"]:
            assert it["about"] and it["name"] and it["code"] == "photo: " + it["key"]
