import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def no_private_overlay(tmp_path_factory):
    """Tests never see a developer's own local/ folder (app/overlay.py); tests of the overlay point it elsewhere."""
    empty = tmp_path_factory.mktemp("no-local")
    os.environ["FRAME_LOCAL_DIR"] = str(empty)
    yield empty
    os.environ.pop("FRAME_LOCAL_DIR", None)


@pytest.fixture
def demo_env(tmp_path, monkeypatch):
    """Demo settings with a throwaway data folder."""
    monkeypatch.setenv("FRAME_DEMO", "1")
    monkeypatch.setenv("FRAME_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FRAME_PHOTOS_DIR", str(tmp_path / "photos"))  # never touch the real photos/ folder
    for k in ("FRAME_ADDON", "SUPERVISOR_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    for k in ("FRAME_NOW", "FRAME_PIN_HASH"):
        monkeypatch.delenv(k, raising=False)
    import importlib

    import app.config
    importlib.reload(app.config)
    yield tmp_path
    importlib.reload(app.config)


@pytest.fixture
def settings(demo_env):
    from app.config import load_settings
    return load_settings()


@pytest.fixture
def db(tmp_path):
    from app.db import Database
    return Database(tmp_path / "t.db")


@pytest.fixture(scope="session", autouse=True)
def optional_art_packs(tmp_path_factory):
    """Every downloadable art pack, installed from its zip into a folder every test sees (FRAME_EXTRA_PACKS),
    so the tests run with every picture and rule there is. The Faith pack is on by default in a real
    Doorpost (installed the first time it starts, app/packs.py seed_defaults); Outings and Kids' activities
    are optional downloads, here so their pictures and rules are tested too. Tests that need the
    first-start behavior, or a pack missing, take the folder away with monkeypatch.delenv("FRAME_EXTRA_PACKS")
    (tests/test_packs.py: fresh and bare)."""
    from app import pack_build as pb, packs as P
    work = tmp_path_factory.mktemp("pack-build")
    dest = tmp_path_factory.mktemp("extra-packs")
    for pid in pb.OPTIONAL:
        z, _sha = pb.build_zip(pid, work, work)
        P.install_zip(z.read_bytes(), demo=False, dest_root=dest)
    os.environ["FRAME_EXTRA_PACKS"] = str(dest)
    yield dest
    os.environ.pop("FRAME_EXTRA_PACKS", None)
