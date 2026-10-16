"""One Google sign-in for everything that uses Google: the Photos Picker and Google Tasks.

Settings has one "Connect Google" button. It asks Google for the parts the family wants (Photos Picker, Tasks)
with include_granted_scopes=true, so a later "allow Tasks too" adds to the same sign-in instead of replacing it.

Setup (once, in Google Cloud): a project with the "Photos Picker API" and the "Google Tasks API" turned on, and an
OAuth client of type "Web application" whose redirect address is <frame address>/api/google/callback (Settings
shows the exact one). Google only allows https addresses there (or localhost).

The sign-in is kept in DATA_DIR/google.json (a refresh token and the list of allowed scopes). It never goes to the
browser. Disconnect revokes it at Google and removes the file.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from pathlib import Path
from typing import Iterable, Optional

import httpx

log = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# What each feature needs. Tasks needs full access (not tasks.readonly): the frame checks items off and adds them.
SCOPES = {
    "photos": "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
    "tasks": "https://www.googleapis.com/auth/tasks",
}
FEATURE_NAMES = {"photos": "Google Photos", "tasks": "Google Tasks"}


class GoogleError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class GoogleAccount:
    """The family's Google sign-in. `http` can be an httpx.Client (tests pass one with a mock transport)."""

    def __init__(self, token_file: Path, client_id: str, client_secret: str, base_url: str, secret: str,
                 http: Optional[httpx.Client] = None):
        self.token_file = token_file
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.base_url = (base_url or "").rstrip("/")
        self._secret = secret.encode()
        self.http = http or httpx   # the module has the same get/post/request functions as a Client
        legacy = token_file.with_name("google-photos" + token_file.suffix)
        if not token_file.exists() and legacy.exists():   # sign-ins made before Tasks existed
            try:
                legacy.replace(token_file)
            except OSError:
                pass

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.base_url)

    @property
    def redirect_uri(self) -> str:
        return f"{self.base_url}/api/google/callback"

    # ---------- the saved sign-in ----------

    def _tokens(self) -> dict:
        try:
            return json.loads(self.token_file.read_text())
        except (OSError, ValueError):
            return {}

    def _save(self, t: dict) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.token_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(t))
        tmp.chmod(0o600)
        tmp.replace(self.token_file)

    @property
    def connected(self) -> bool:
        return bool(self._tokens().get("refresh_token"))

    def granted(self) -> set[str]:
        """The features this sign-in covers ("photos", "tasks")."""
        t = self._tokens()
        if not t.get("refresh_token"):
            return set()
        if not t.get("scope"):   # a google-photos.json from before Tasks, saved without the scope: it was for Photos
            return {"photos"}
        have = set(t["scope"].split())
        return {f for f, sc in SCOPES.items() if sc in have}

    def has(self, feature: str) -> bool:
        return feature in self.granted()

    # ---------- signing in ----------

    def state(self, who: str = "") -> str:
        ts = str(int(time.time()))
        sig = hmac.new(self._secret, f"google|{ts}|{who}".encode(), hashlib.sha256).hexdigest()[:32]
        return f"{ts}.{sig}.{urllib.parse.quote(who, safe='')}"

    def check_state(self, state: str) -> bool:
        try:
            ts, sig, who = state.split(".", 2)
        except ValueError:
            return False
        good = hmac.new(self._secret, f"google|{ts}|{urllib.parse.unquote(who)}".encode(), hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(sig, good) and time.time() - int(ts) < 900

    def auth_url(self, features: Iterable[str] = ("photos", "tasks")) -> str:
        """Google's sign-in page, asking for these features on top of whatever was allowed before."""
        if not self.configured:
            raise GoogleError("Add the Google client ID and secret first.")
        want = [SCOPES[f] for f in features if f in SCOPES] or list(SCOPES.values())
        q = {"client_id": self.client_id, "redirect_uri": self.redirect_uri, "response_type": "code", "scope": " ".join(want),
             "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true", "state": self.state()}
        return AUTH_URL + "?" + urllib.parse.urlencode(q)

    def finish(self, code: str) -> set[str]:
        r = self.http.post(TOKEN_URL, data={"code": code, "client_id": self.client_id, "client_secret": self.client_secret,
                                            "redirect_uri": self.redirect_uri, "grant_type": "authorization_code"}, timeout=20)
        if r.status_code != 200:
            raise GoogleError(f"Google said no ({r.status_code}): {r.text[:200]}", r.status_code)
        t = r.json()
        old = self._tokens()
        if not t.get("refresh_token"):
            if not old.get("refresh_token"):
                raise GoogleError("Google didn't send a lasting sign-in. Remove Doorpost from your Google account's "
                                  "third-party access page and connect again.")
            t["refresh_token"] = old["refresh_token"]
        t["expires_at"] = time.time() + int(t.get("expires_in", 3600)) - 60
        self._save(t)
        return self.granted()

    def access_token(self) -> str:
        t = self._tokens()
        if not t.get("refresh_token"):
            raise GoogleError("Connect Google first (Settings).")
        if t.get("access_token") and t.get("expires_at", 0) > time.time():
            return t["access_token"]
        r = self.http.post(TOKEN_URL, data={"client_id": self.client_id, "client_secret": self.client_secret,
                                            "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=20)
        if r.status_code != 200:
            # An app left in Google's "Testing" mode loses its sign-in after 7 days: connect again.
            raise GoogleError("Google needs to be connected again (the sign-in expired or was removed).", r.status_code)
        n = r.json()
        t.update(access_token=n["access_token"], expires_at=time.time() + int(n.get("expires_in", 3600)) - 60)
        if n.get("scope"):
            t["scope"] = n["scope"]
        self._save(t)
        return t["access_token"]

    def disconnect(self) -> None:
        t = self._tokens()
        if t.get("refresh_token"):
            try:
                self.http.post(REVOKE_URL, data={"token": t["refresh_token"]}, timeout=10)
            except httpx.HTTPError:
                pass
        for f in (self.token_file, self.token_file.with_name("google-photos" + self.token_file.suffix)):
            try:   # the older version's file too (app/compat.py keeps a copy): it holds the same sign-in
                f.unlink()
            except FileNotFoundError:
                pass

    # ---------- calling Google ----------

    def call(self, method: str, url: str, what: str = "Google", **kw) -> dict:
        """One API call with the saved sign-in. Raises GoogleError with Google's status code on failure."""
        try:
            r = self.http.request(method, url, headers={"Authorization": f"Bearer {self.access_token()}"}, timeout=30, **kw)
        except httpx.HTTPError as exc:
            raise GoogleError(f"Couldn't reach {what}: {exc.__class__.__name__}")
        if r.status_code >= 400:
            msg = r.text[:200]
            try:
                msg = r.json().get("error", {}).get("message") or msg
            except (ValueError, AttributeError):
                pass
            raise GoogleError(f"{what} error {r.status_code}: {msg}", r.status_code)
        return r.json() if r.content else {}

    def get_bytes(self, url: str) -> bytes:
        r = self.http.get(url, headers={"Authorization": f"Bearer {self.access_token()}"}, timeout=60, follow_redirects=True)
        if r.status_code != 200:
            raise GoogleError(f"Couldn't download from Google ({r.status_code}).", r.status_code)
        return r.content
