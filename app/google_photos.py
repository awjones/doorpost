"""Google Photos Picker: the only way an app can get photos out of a Google Photos library since March 31, 2025.

The frame opens a picking session, a parent picks photos in Google Photos (phone or computer) and taps Done,
and the frame downloads just those. Used two ways:
- birthday portraits (Settings > Family): the frame keeps the newest picked photo with one face (app/portraits.py);
- the slideshow (Settings > Photos): every picked photo is copied into the photos folder (app/photo_picks.py).

Google doesn't let any app read face groups, favorites or the whole library any more, so picking by hand (plus
shared-album links, app/photo_sources.py) is how Google photos reach the frame. The sign-in is shared with
Google Tasks: see app/google_auth.py.
"""
from __future__ import annotations

from .google_auth import SCOPES, GoogleAccount, GoogleError  # noqa: F401  (GoogleError is imported from here too)

PICKER = "https://photospicker.googleapis.com/v1"
SCOPE = SCOPES["photos"]
MAX_PICKED = 30          # portraits: look at no more than this many of the picked photos (newest first)


class GooglePhotos:
    def __init__(self, account: GoogleAccount):
        self.account = account

    def _call(self, method: str, path: str, **kw) -> dict:
        if not self.account.has("photos") and self.account.connected:
            raise GoogleError("The Google sign-in doesn't include Google Photos yet. Press Connect Google again and allow it.")
        return self.account.call(method, PICKER + path, what="Google Photos", **kw)

    def new_session(self) -> dict:
        s = self._call("POST", "/sessions", json={})
        return {"id": s["id"], "uri": s["pickerUri"], "poll": float(s.get("pollingConfig", {}).get("pollInterval", "4s").rstrip("s") or 4)}

    def session_done(self, sid: str) -> bool:
        return bool(self._call("GET", f"/sessions/{sid}").get("mediaItemsSet"))

    def picked(self, sid: str) -> list[dict]:
        items, page = [], None
        while True:
            params = {"sessionId": sid, "pageSize": 100}
            if page:
                params["pageToken"] = page
            r = self._call("GET", "/mediaItems", params=params)
            items += [i for i in r.get("mediaItems", []) if i.get("type", "PHOTO") == "PHOTO"]
            page = r.get("nextPageToken")
            if not page:
                return items

    def download(self, item: dict, size: int = 1600) -> bytes:
        """A picked photo, at most size x size (Google keeps the shape). Picked items are only downloadable for a while."""
        try:
            return self.account.get_bytes(item["mediaFile"]["baseUrl"] + f"=w{size}-h{size}")
        except GoogleError as exc:
            raise GoogleError(f"Couldn't download a picked photo ({exc.status}).", exc.status)

    def end_session(self, sid: str) -> None:
        try:
            self._call("DELETE", f"/sessions/{sid}")
        except GoogleError:
            pass
