"""The private overlay: a `local/` folder for one household's own settings, scripts, art and branding.

The public code never needs it. A family that keeps a private copy of the code puts their own files in
`local/` (git-ignored, see docs/private-overlay.md) and the app reads them first:

    local/config/frame.yaml      read before config/frame.yaml (chores.yaml the same way); not in demo mode
    local/.env                   read before .env (secrets for a non-add-on install)
    local/packs/<id>/            private art packs (app/packs.py)
    local/themes/<name>/         private looks
    local/web/                   files served in place of web/ files of the same path, e.g. img/monogram.png
    local/addon/                 add-on build settings (scripts/build-addon.sh): addon.conf, icon.png, logo.png

FRAME_LOCAL_DIR points somewhere else (the tests use an empty folder, so a developer's own local/ never
changes a test). Everything here is looked up when it is needed, so changing the variable takes effect at once.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent


def local_dir() -> Path:
    return Path(os.environ.get("FRAME_LOCAL_DIR") or ROOT / "local").expanduser()


def config_file(name: str) -> Optional[Path]:
    """local/config/<name>.yaml, when there is one."""
    p = local_dir() / "config" / f"{name}.yaml"
    return p if p.is_file() else None


def env_file() -> Path:
    return local_dir() / ".env"


def packs_dir() -> Path:
    return local_dir() / "packs"


def themes_dir() -> Path:
    return local_dir() / "themes"


def web_dir() -> Optional[Path]:
    """local/web/, when it exists: its files win over web/ files of the same path."""
    p = local_dir() / "web"
    return p if p.is_dir() else None


def summary() -> dict:
    """What the overlay adds, for logs and the compatibility check (names only, never contents)."""
    d = local_dir()
    if not d.is_dir():
        return {"folder": str(d), "present": False}
    packs = sorted(p.name for p in packs_dir().iterdir() if (p / "pack.json").is_file()) if packs_dir().is_dir() else []
    themes = sorted(p.name for p in themes_dir().iterdir() if p.is_dir()) if themes_dir().is_dir() else []
    web = web_dir()
    return {"folder": str(d), "present": True,
            "config": [n for n in ("frame", "chores") if config_file(n)],
            "env": env_file().is_file(), "packs": packs, "themes": themes,
            "web": sorted(str(p.relative_to(web)) for p in web.rglob("*") if p.is_file()) if web else []}
