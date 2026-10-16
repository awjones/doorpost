"""Live photo feeds from shared albums.

Neither Google nor Apple offers an official way to read a family album any
more (Google removed library read access from its Photos API on 2025-03-31;
Apple has never had one). Both still publish albums shared *by link*, and this
reads those pages the way a browser does. That is unofficial: if a provider
changes its page, the source shows an error in the admin panel and the frame
keeps showing the photos it already has.

Each function returns [{"key": stable id, "url": full-size image url}].
"""
from __future__ import annotations

import re
from typing import Optional

import httpx

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


class SourceError(Exception):
    pass


# ---------------- Google Photos: album shared by link ----------------

_G_ITEM = re.compile(r'\["(AF1Qip[\w-]+)",\["(https://lh3\.googleusercontent\.com/[^"]+)",(\d+),(\d+)')
_G_URL = re.compile(r'https://lh3\.googleusercontent\.com/pw/[\w-]{40,}')


def google_album(url: str, http: Optional[httpx.Client] = None) -> list[dict]:
    """photos.app.goo.gl/... or photos.google.com/share/... link."""
    if not re.match(r"https://(photos\.app\.goo\.gl|photos\.google\.com|goo\.gl)/", url or ""):
        raise SourceError("That doesn't look like a Google Photos share link (photos.app.goo.gl/…).")
    http = http or httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    r = http.get(url)
    if r.status_code != 200:
        raise SourceError(f"Google Photos returned {r.status_code}. Is the link still shared?")
    return parse_google_album(r.text)


def parse_google_album(html: str) -> list[dict]:
    items, seen = [], set()
    for key, img, w, h in _G_ITEM.findall(html):
        if key in seen or int(w) < 300:
            continue
        seen.add(key)
        items.append({"key": "g-" + key, "url": img.split("=")[0] + "=w1920-h1200"})
    if not items:  # page layout changed: fall back to any full-size photo URL on the page
        for img in dict.fromkeys(_G_URL.findall(html)):
            items.append({"key": "g-" + img.rsplit("/", 1)[-1][:40], "url": img + "=w1920-h1200"})
    if not items:
        raise SourceError("No photos found on that album page (Google may have changed it).")
    return items


# ---------------- iCloud: Shared Album with "Public Website" on ----------------

_B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def icloud_token(url: str) -> str:
    # Newer links use a longer code with - and _ (e.g. #D2…-BI…_…); older ones are letters and digits.
    m = re.search(r"#([A-Za-z0-9_-]{10,})", url or "") or re.search(r"sharedalbum/#?([A-Za-z0-9_-]{10,})", url or "")
    if not m:
        raise SourceError("That doesn't look like an iCloud shared album link (icloud.com/sharedalbum/#…).")
    return m.group(1)


def icloud_host(token: str) -> str:
    def b62(s: str) -> int:
        n = 0
        for ch in s:
            n = n * 62 + _B62.index(ch)
        return n
    partition = b62(token[1]) if token[0] == "A" else b62(token[1:3])
    return f"p{partition:02d}-sharedstreams.icloud.com"


def icloud_album(url: str, http: Optional[httpx.Client] = None) -> list[dict]:
    token = icloud_token(url)
    http = http or httpx.Client(timeout=30, headers={"User-Agent": UA, "Content-Type": "text/plain"})
    host = icloud_host(token)
    r = http.post(f"https://{host}/{token}/sharedstreams/webstream", content='{"streamCtag":null}')
    if r.status_code == 330:  # Apple says: use this other server
        host = r.json().get("X-Apple-MMe-Host") or r.headers.get("X-Apple-MMe-Host") or host
        r = http.post(f"https://{host}/{token}/sharedstreams/webstream", content='{"streamCtag":null}')
    if r.status_code != 200:
        raise SourceError(f"iCloud returned {r.status_code}. Is Public Website turned on for the album?")
    photos = r.json().get("photos", [])
    best = {}
    for p in photos:
        if p.get("mediaAssetType") == "video":
            continue
        ders = p.get("derivatives", {})
        if not ders:
            continue
        top = max(ders.values(), key=lambda d: int(d.get("width", 0) or 0))
        best[p["photoGuid"]] = top["checksum"]
    if not best:
        raise SourceError("The album is empty, or iCloud didn't return any photos.")
    r = http.post(f"https://{host}/{token}/sharedstreams/webasseturls",
                  content='{"photoGuids":[' + ",".join(f'"{g}"' for g in best) + "]}")
    if r.status_code != 200:
        raise SourceError(f"iCloud returned {r.status_code} for the photo addresses.")
    return parse_icloud_urls(best, r.json())


def parse_icloud_urls(best: dict[str, str], asset_json: dict) -> list[dict]:
    items = asset_json.get("items", {})
    out = []
    for guid, checksum in best.items():
        it = items.get(checksum)
        if it:
            out.append({"key": "i-" + guid, "url": f"https://{it['url_location']}{it['url_path']}"})
    return out


FETCHERS = {"google_album": google_album, "icloud_album": icloud_album}
