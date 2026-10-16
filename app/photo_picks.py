"""Photos picked in Google Photos, copied into the slideshow (Settings > Photos > Pick photos from Google Photos).

Since March 31, 2025 Google lets an app see only the photos a person picks by hand in Google's own picker
(app/google_photos.py). The frame opens a picking session; when the parent taps Done, a background job downloads
every picked photo at a frame-friendly size (at most 2048 px on the long side) into photos/google-picks/.

A record (photos/google-picks/picked.json: Google's id for the photo -> file name) means picking the same photo
again later doesn't copy it twice. Removing a photo from the frame and picking it again brings it back.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import threading
from pathlib import Path
from typing import Optional

from PIL import Image

from .google_photos import GoogleError, GooglePhotos

log = logging.getLogger(__name__)
SUB = "google-picks"
SIZE = 2048
_JOBS: dict[str, dict] = {}     # picking session id -> progress, for Settings to poll
_LOCK = threading.Lock()


class PickImport:
    def __init__(self, photos_folder: Path):
        self.folder = photos_folder / SUB
        self.record_file = self.folder / "picked.json"

    def record(self) -> dict:
        try:
            return json.loads(self.record_file.read_text())
        except (OSError, ValueError):
            return {}

    def _save_record(self, rec: dict) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = self.record_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, indent=1))
        tmp.replace(self.record_file)

    @staticmethod
    def file_name(item: dict) -> str:
        """A stable, safe file name: a short hash of Google's id plus the photo's own name."""
        base = (item.get("mediaFile") or {}).get("filename") or "photo"
        base = re.sub(r"[^A-Za-z0-9_-]+", "-", base.rsplit(".", 1)[0]).strip("-")[:40] or "photo"
        return f"{hashlib.sha1(item['id'].encode()).hexdigest()[:10]}-{base}.jpg"

    def run(self, gp: GooglePhotos, sid: str, job: Optional[dict] = None) -> dict:
        """Download what was picked in this session. Fills and returns `job`: total, added, skipped, failed."""
        job = job if job is not None else {}
        items = gp.picked(sid)
        job.update(total=len(items), added=0, skipped=0, failed=0, state="downloading")
        rec = self.record()
        for it in items:
            name = rec.get(it["id"])
            if name and (self.folder / name).exists():
                job["skipped"] += 1
                continue
            try:
                data = gp.download(it, SIZE)
                with Image.open(io.BytesIO(data)) as im:
                    im.verify()
            except (GoogleError, Exception) as exc:  # one bad photo shouldn't stop the rest
                log.info("Google pick not copied: %s", exc)
                job["failed"] += 1
                continue
            name = self.file_name(it)
            self.folder.mkdir(parents=True, exist_ok=True)
            (self.folder / name).write_bytes(data)
            rec[it["id"]] = name
            self._save_record(rec)
            job["added"] += 1
        gp.end_session(sid)
        job["state"] = "done"
        return job


def poll(gp: GooglePhotos, photos_folder: Path, sid: str, on_done=None) -> dict:
    """Settings asks every few seconds: still picking, copying (with counts), or done."""
    with _LOCK:
        job = _JOBS.get(sid)
        if job is None:
            if not gp.session_done(sid):
                return {"state": "picking"}
            job = _JOBS[sid] = {"state": "downloading", "total": 0, "added": 0, "skipped": 0, "failed": 0}

            def work():
                try:
                    PickImport(photos_folder).run(gp, sid, job)
                except GoogleError as exc:
                    job.update(state="error", message=str(exc))
                if on_done:
                    on_done()
            threading.Thread(target=work, daemon=True).start()
        out = dict(job)
    if out["state"] in ("done", "error"):
        _JOBS.pop(sid, None)
    return out
