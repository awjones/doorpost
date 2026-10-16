"""Settings API for the Apple / Google choices: the shared Google sign-in, Google Tasks lists and Google Photos picks.

The Google client ID, secret and sign-in endpoints themselves live in app/admin.py (/api/admin/google...).
The client secret and the sign-in tokens are never sent to the browser: only whether they're saved.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .config import read_store
from .main import Services, require_admin, svc

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


def google_view(s: Services) -> dict:
    """What Settings shows about the Google connection (no secrets)."""
    g = s.google()
    sec = read_store(s.settings.demo).get("secrets", {})
    granted = sorted(g.granted())
    return {"client_id": g.client_id, "has_secret": bool(sec.get("google_client_secret")),
            "redirect_uri": g.redirect_uri if g.base_url else "", "frame_url": g.base_url,
            "connected": g.connected, "granted": granted, "demo": s.settings.demo}


def lists_sources(s: Services) -> dict:
    """Settings > Lists: where lists can come from and how each one is doing."""
    L = s.lists
    now = s.now().replace(tzinfo=None)

    def ago(src):
        at = L.synced_at(src)
        return int((now - at).total_seconds()) if at else None
    avail = L.available()
    g = google_view(s)
    return {"google": g, "sources": {
        "apple": {"lists": sum(1 for a in avail if a["source"] == "apple"), "synced_ago": ago("apple")},
        "google": {"lists": sum(1 for a in avail if a["source"] == "google"), "synced_ago": ago("google"),
                   "on": L.google_on, "ready": s.settings.demo or "tasks" in g["granted"], "error": L.error("google")},
    }}


@router.get("/google")
def get_google(s: Services = Depends(svc)):
    return google_view(s)


@router.post("/lists/google/sync")
def lists_google_sync(s: Services = Depends(svc)):
    """Settings > Lists > Check now: read Google Tasks right away."""
    s.sync_google_tasks()
    err = s.lists.error("google")
    if err:
        return {"ok": False, "message": err}
    n = sum(1 for a in s.lists.available() if a["source"] == "google")
    return {"ok": True, "message": f"Connected: {n} Google Tasks list{'s' if n != 1 else ''}."}


# ---------------- Settings > Photos > Pick photos from Google Photos ----------------

@router.post("/photos/google")
def photos_pick_start(s: Services = Depends(svc)):
    """Open a Google Photos picking session for the slideshow."""
    from .google_photos import GoogleError
    if s.settings.demo:
        raise HTTPException(400, "Demo mode doesn't connect to Google. With a real Google sign-in, this opens Google Photos "
                                 "so you can pick photos for the slideshow.")
    try:
        return s.google_photos().new_session()
    except GoogleError as exc:
        raise HTTPException(400, str(exc))


@router.get("/photos/google/{sid}")
def photos_pick_poll(sid: str, s: Services = Depends(svc)):
    """Still picking, copying the picked photos (with counts), or done."""
    from .google_photos import GoogleError
    from .photo_picks import poll

    def rescan():
        s.photos.maybe_rescan(0)
    try:
        return poll(s.google_photos(), s.settings.photos_folder, sid, on_done=rescan)
    except GoogleError as exc:
        raise HTTPException(400, str(exc))
