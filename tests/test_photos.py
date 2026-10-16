from PIL import Image

from app.photos import PhotoLibrary


def test_photos_are_resized_and_captioned(tmp_path):
    folder = tmp_path / "photos"
    (folder / "2025").mkdir(parents=True)
    Image.new("RGB", (4000, 3000), (120, 80, 40)).save(folder / "2025" / "lake.jpg")
    Image.new("RGB", (800, 1200), (10, 80, 140)).save(folder / "tall.png")
    (folder / "captions.yaml").write_text("lake.jpg: Lake trip · July 2025\n")
    (folder / "notes.txt").write_text("not a photo")

    lib = PhotoLibrary(folder, tmp_path / "cache")
    items = lib.scan()
    assert len(items) == 2
    caps = {i["caption"] for i in items}
    assert "Lake trip · July 2025" in caps
    for i in items:
        out = lib.file_for(i["id"])
        with Image.open(out) as im:
            assert im.size == (1280, 800)
    assert lib.file_for("missing") is None


def test_settings_thumbnails_are_small_and_newest_first(tmp_path):
    folder = tmp_path / "photos" / "apple-favorites"
    folder.mkdir(parents=True)
    for name in ("20240101-090000-a.jpg", "20260704-120000-b.jpg", "20250520-080000-c.jpg"):
        Image.new("RGB", (3000, 2000), (90, 60, 30)).save(folder / name)
    lib = PhotoLibrary(tmp_path / "photos", tmp_path / "cache")
    lib.scan()
    names = [p["name"].rsplit("/", 1)[-1] for p in lib.admin_listing()]
    assert names == ["20260704-120000-b.jpg", "20250520-080000-c.jpg", "20240101-090000-a.jpg"]
    pid = lib.admin_listing()[0]["id"]
    with Image.open(lib.file_for(pid, thumb=True)) as im:
        assert im.size == (320, 200)
    assert lib.remove(pid) and not (tmp_path / "cache" / f"{pid}-t.jpg").exists()


def test_index_survives_a_settings_save_and_a_restart(tmp_path, monkeypatch):
    folder = tmp_path / "photos"
    folder.mkdir()
    Image.new("RGB", (1500, 1000), (90, 60, 30)).save(folder / "a.jpg")
    first = PhotoLibrary(folder, tmp_path / "cache")
    first.scan()
    # A saved setting builds a new library: it takes the old index and doesn't open the photos again.
    second = PhotoLibrary(folder, tmp_path / "cache")
    second.adopt(first)
    monkeypatch.setattr(PhotoLibrary, "_exif_info", staticmethod(lambda p: (_ for _ in ()).throw(AssertionError("re-read"))))
    second.maybe_rescan()
    assert len(second.listing()) == 1
    # A restart reads the saved index from the cache folder instead.
    third = PhotoLibrary(folder, tmp_path / "cache")
    assert len(third.scan()) == 1 and third._local[third.listing()[0]["id"]]["w"] == 1500
