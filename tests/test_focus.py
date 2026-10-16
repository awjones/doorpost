"""Focal points: one point per photo drives both crops; either crop can be moved or set to show the whole photo."""
from PIL import Image

from app.db import Database
from app.photos import FocusStore, PhotoLibrary, crop_rect, render


def lib(tmp_path):
    folder = tmp_path / "photos"
    (folder / "apple-favorites").mkdir(parents=True)
    # A wide 3:2 photo: red on the left third, blue on the right third.
    im = Image.new("RGB", (1500, 1000), (0, 160, 0))
    im.paste((220, 0, 0), (0, 0, 500, 1000))
    im.paste((0, 0, 220), (1000, 0, 1500, 1000))
    im.save(folder / "apple-favorites" / "20240101-120000-ABC.jpg", "JPEG")
    L = PhotoLibrary(folder, tmp_path / "cache", focus=FocusStore(Database(tmp_path / "t.db")))
    L.scan()
    return L


def test_crop_rect():
    # 3:2 photo on a tall 10:16 frame: a narrow slice, centered where asked, kept inside the photo.
    left, top, cw, ch = crop_rect(1500, 1000, "tall", 0.85, 0.5)
    assert round(cw, 4) == round(0.625 / 1.5, 4) and ch == 1.0 and round(left + cw, 4) == 1.0
    assert crop_rect(1500, 1000, "tall", 0.5, 0.5)[0] == (1 - cw) / 2
    # A tall photo on a wide frame crops top and bottom.
    left, top, cw, ch = crop_rect(1000, 1500, "wide", 0.5, 0.0)
    assert cw == 1.0 and top == 0.0 and round(ch, 4) == round((1000 / 1500) / 1.6, 4)


def test_point_faces_and_overrides(tmp_path):
    L = lib(tmp_path)
    pid = L.listing()[0]["id"]
    assert "v" not in L.listing()[0]
    name = L._local[pid]["name"]
    tall = Image.open(L.file_for(pid, shape="tall"))
    assert tall.size == (800, 1280) and tall.getpixel((400, 640))[1] > 120          # middle: green
    L.focus.set(name, faces=[0.9, 0.5]); L.drop_variants(pid)                     # faces on the right
    assert Image.open(L.file_for(pid, shape="tall")).getpixel((400, 640))[2] > 150  # blue
    L.focus.set(name, point=[0.1, 0.5]); L.drop_variants(pid)                     # set by hand wins
    assert Image.open(L.file_for(pid, shape="tall")).getpixel((400, 640))[0] > 150  # red
    L.focus.set(name, tall=[0.5, 0.5]); L.drop_variants(pid)                      # tall crop moved on its own
    assert Image.open(L.file_for(pid, shape="tall")).getpixel((400, 640))[1] > 120
    assert L.listing()[0]["v"] == FocusStore.version(L.focus.get(name))
    L.focus.set(name, tall_fit=True); L.drop_variants(pid)                        # whole photo, soft edges
    fit = Image.open(L.file_for(pid, shape="tall"))
    assert fit.size == (800, 1280) and fit.getpixel((400, 100)) != fit.getpixel((400, 640))
    assert Image.open(L.file_for(pid, shape="wide")).size == (1280, 800)
    assert max(Image.open(L.file_for(pid, shape="edit")).size) == 1200
    assert "tall" in L.shapes


def test_full_hd_shapes_follow_the_same_choices(tmp_path):
    L = lib(tmp_path)
    pid = L.listing()[0]["id"]
    name = L._local[pid]["name"]
    L.focus.set(name, tall=[0.9, 0.5]); L.drop_variants(pid)
    hd = Image.open(L.file_for(pid, shape="tall-hd"))
    assert hd.size == (1080, 1920) and hd.getpixel((540, 960))[2] > 150   # follows the tall crop: blue
    assert Image.open(L.file_for(pid, shape="wide-hd")).size == (1920, 1080)
    assert {"tall-hd", "wide-hd"} <= L.shapes
